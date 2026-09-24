from typing import Optional, List, Dict, Any
import random
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import User, CompanyProfile, Role
from shared.schemas import (
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    ChangePasswordRequest,
    VerifyEmailRequest,
    SendVerificationEmailRequest,
    APIResponse,
)
from pydantic import BaseModel, EmailStr, Field
from shared.utils import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    get_current_active_user_optional,
    send_verification_email,
    success_response,
    log_audit_event,
)

router = APIRouter(prefix="/auth", tags=["Company Auth"])

# In-memory verification cache: email -> { "code": str, "expires_at": datetime }
_VERIFICATION_CACHE: Dict[str, dict] = {}

class CompanyRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    company_name: str = Field(..., min_length=1, max_length=255)
    contact_name: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    company_size: Optional[str] = None
    website: Optional[str] = None
    reg_number: Optional[str] = None

@router.post("/register", response_model=APIResponse[dict])
def register_company(req: CompanyRegisterRequest, request: Request, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists",
        )
    
    contact_name = req.contact_name or req.full_name or req.company_name or "Representative"
    parts = contact_name.strip().split(" ", 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ""
    
    company_name = req.company_name or "New Company"
    company_role = db.query(Role).filter(Role.code == "company").first()
    roles = [company_role] if company_role else []
    
    user = User(
        email=req.email.lower(),
        hashed_password=hash_password(req.password),
        first_name=first_name,
        last_name=last_name,
        phone=req.phone,
        user_type="company",
        is_active=True,
        is_verified=False,
        roles=roles,
    )
    db.add(user)
    db.flush()

    # Create company profile with pending verification
    profile = CompanyProfile(
        user_id=user.id,
        company_name=company_name,
        industry=req.industry or "Technology",
        company_size=req.size or req.company_size or "11-50",
        website=req.website,
        verification_status="pending",
    )
    db.add(profile)
    db.commit()
    db.refresh(user)

    # Generate and send 6-digit email verification code
    code = f"{random.randint(100000, 999999)}"
    _VERIFICATION_CACHE[user.email.lower()] = {
        "code": code,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=15),
    }
    send_verification_email(to_email=user.email, code=code, name=contact_name)

    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        user_type="company",
        roles=["company"],
    )
    refresh_token = create_refresh_token(user.id)

    log_audit_event(
        db,
        action="REGISTER",
        module="COMPANY_AUTH",
        description=f"New company registered: {company_name} ({user.email})",
        user_id=user.id,
        user_email=user.email,
        user_type="company",
        request=request,
    )

    return success_response(
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "user_type": user.user_type,
                "company_id": profile.id,
                "company_name": profile.company_name,
            },
        },
        message="Company account created successfully",
    )


@router.post("/login", response_model=APIResponse[dict])
def login_company(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.lower()).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your company account is inactive. Please contact administrator.",
        )

    roles = [r.code for r in user.roles]
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        user_type=user.user_type,
        roles=roles,
    )
    refresh_token = create_refresh_token(user.id)

    log_audit_event(
        db,
        action="LOGIN",
        module="COMPANY_AUTH",
        description=f"Company recruiter logged in: {user.email}",
        user_id=user.id,
        user_email=user.email,
        user_type=user.user_type,
        request=request,
    )

    company_id = user.company_profile.id if user.company_profile else None
    company_name = user.company_profile.company_name if user.company_profile else None

    return success_response(
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "user_type": user.user_type,
                "company_id": company_id,
                "company_name": company_name,
            },
        },
        message="Login successful",
    )


class LoginInitiateRequest(BaseModel):
    email: EmailStr
    password: str

class VerifyOtpRequest(BaseModel):
    session_token: str
    code: str

@router.post("/login/initiate", response_model=APIResponse[dict])
def initiate_otp_login(req: LoginInitiateRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.lower()).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your company account is inactive. Please contact administrator.",
        )

    if user.company_profile:
        v_status = (user.company_profile.verification_status or "").lower()
        if v_status == "pending":
            return success_response(
                data={
                    "status": "PENDING_APPROVAL",
                    "session_token": None,
                },
                message="Your company registration is pending approval.",
            )
        elif v_status == "rejected":
            return success_response(
                data={
                    "status": "REJECTED",
                    "session_token": None,
                },
                message="Your company registration was not approved.",
            )

    email = user.email
    name, domain = email.split("@") if "@" in email else (email, "")
    masked_email = f"{name[:1]}•••@{domain}" if domain else email

    # Mock OTP logic
    return success_response(
        data={
            "session_token": f"mock_session_{user.id}",
            "status": "OTP_SENT",
            "masked_email": masked_email,
        },
        message="OTP sent to email/phone",
    )

@router.post("/login/verify-otp", response_model=APIResponse[dict])
def verify_otp_login(req: VerifyOtpRequest, request: Request, db: Session = Depends(get_db)):
    # Mock OTP verification
    if not req.session_token.startswith("mock_session_"):
        raise HTTPException(status_code=400, detail="Invalid session token")
    
    if req.code not in ["1234", "123456"]:
        raise HTTPException(status_code=400, detail="Invalid OTP code. Please enter 123456.")
        
    user_id = int(req.session_token.split("_")[-1])
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Your company account is inactive. Please contact administrator.")

    roles = [r.code for r in user.roles]
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        user_type=user.user_type,
        roles=roles,
    )
    refresh_token = create_refresh_token(user.id)
    
    company_id = user.company_profile.id if user.company_profile else None
    company_name = user.company_profile.company_name if user.company_profile else None

    return success_response(
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "user_type": user.user_type,
                "company_id": company_id,
                "company_name": company_name,
            },
        },
        message="OTP verified successfully",
    )


@router.post("/send-verification-email", response_model=APIResponse[dict])
@router.post("/resend-verification-email", response_model=APIResponse[dict])
def send_company_verification_email_route(
    req: SendVerificationEmailRequest = None,
    current_user: Optional[User] = Depends(get_current_active_user_optional),
    db: Session = Depends(get_db),
):
    target_email = ((req.email or "") if req else "").strip().lower()
    if not target_email and current_user:
        target_email = current_user.email.strip().lower()

    if not target_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is required to send verification code",
        )

    user = db.query(User).filter(User.email == target_email).first()
    display_name = user.full_name if user else (current_user.full_name if current_user else "Employer")

    code = f"{random.randint(100000, 999999)}"
    _VERIFICATION_CACHE[target_email] = {
        "code": code,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=15),
    }

    send_verification_email(to_email=target_email, code=code, name=display_name)

    return success_response(
        data={"email": target_email},
        message="Verification code sent to your email",
    )


@router.post("/verify-email", response_model=APIResponse[dict])
def verify_email(
    req: VerifyEmailRequest,
    request: Request,
    current_user: Optional[User] = Depends(get_current_active_user_optional),
    db: Session = Depends(get_db),
):
    target_email = ((req.email or "") if req else "").strip().lower()
    if not target_email and current_user:
        target_email = current_user.email.strip().lower()

    if not target_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is required",
        )

    submitted_code = req.code.strip() if req.code else ""
    cached = _VERIFICATION_CACHE.get(target_email)
    now = datetime.now(timezone.utc)

    # Valid if matches cached unexpired code or dev bypass code "123456" / "1234"
    is_valid_otp = False
    if submitted_code in ["123456", "1234"]:
        is_valid_otp = True
    elif cached and cached.get("code") == submitted_code and now <= cached.get("expires_at"):
        is_valid_otp = True

    if not is_valid_otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code",
        )

    # Clear used OTP
    if target_email in _VERIFICATION_CACHE:
        del _VERIFICATION_CACHE[target_email]

    user = db.query(User).filter(User.email == target_email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_verified = True
    db.commit()
    db.refresh(user)

    log_audit_event(
        db,
        action="VERIFY_EMAIL",
        module="COMPANY_AUTH",
        description=f"Company verified email: {user.email}",
        user_id=user.id,
        user_email=user.email,
        user_type=user.user_type,
        request=request,
    )

    return success_response(
        data={"email": target_email, "is_verified": True},
        message="Email verified successfully",
    )

class ActivateInviteRequest(BaseModel):
    invite_token: str
    name: str
    password: str

@router.get("/invite/{token}", response_model=APIResponse[dict])
def get_invite_by_token(token: str, db: Session = Depends(get_db)):
    # Mock implementation
    return success_response(
        data={
            "email": "invited@example.com",
            "role": "recruiter",
            "company_name": "Sample Company"
        }
    )

@router.post("/activate-invite", response_model=APIResponse[dict])
def activate_team_invite(req: ActivateInviteRequest, db: Session = Depends(get_db)):
    # Mock implementation
    return success_response(
        data={
            "access_token": "mock_token",
            "token_type": "bearer"
        },
        message="Team member account activated"
    )




@router.get("/me", response_model=APIResponse[dict])
def get_company_me(user: User = Depends(get_current_user)):
    profile = user.company_profile
    profile_data = None
    if profile:
        profile_data = {
            "id": profile.id,
            "company_name": profile.company_name,
            "legal_name": profile.legal_name,
            "logo_url": profile.logo_url,
            "cover_image_url": profile.cover_image_url,
            "website": profile.website,
            "industry": profile.industry,
            "company_size": profile.company_size,
            "about": profile.about,
            "address": profile.address,
            "city": profile.city,
            "country": profile.country,
            "verification_status": profile.verification_status,
            "is_featured": profile.is_featured,
        }

    return success_response(
        data={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "user_type": user.user_type,
            "company_profile": profile_data,
        }
    )


@router.post("/refresh", response_model=APIResponse[dict])
def refresh_token(req: RefreshTokenRequest, db: Session = Depends(get_db)):
    payload = decode_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token type")
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not active")
    
    roles = [r.code for r in user.roles]
    new_access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        user_type=user.user_type,
        roles=roles,
    )
    return success_response(data={"access_token": new_access_token, "token_type": "bearer"})


@router.post("/change-password", response_model=APIResponse[None])
def change_password(
    req: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(req.current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    
    user.hashed_password = hash_password(req.new_password)
    db.commit()
    return success_response(message="Password updated successfully")
