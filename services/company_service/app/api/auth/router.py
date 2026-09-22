from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import User, CompanyProfile, Role
from shared.schemas import (
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    ChangePasswordRequest,
    APIResponse,
)
from shared.utils import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    success_response,
    log_audit_event,
)

router = APIRouter(prefix="/auth", tags=["Company Auth"])

@router.post("/register", response_model=APIResponse[dict])
def register_company(req: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists",
        )
    
    company_name = req.company_name or req.full_name or "New Company"
    company_role = db.query(Role).filter(Role.code == "company").first()
    roles = [company_role] if company_role else []
    
    user = User(
        email=req.email.lower(),
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        phone=req.phone,
        user_type="company",
        is_active=True,
        is_verified=True,
        roles=roles,
    )
    db.add(user)
    db.flush()

    # Create company profile with pending verification
    profile = CompanyProfile(
        user_id=user.id,
        company_name=company_name,
        verification_status="verified",  # Default verified in local dev setup
    )
    db.add(profile)
    db.commit()
    db.refresh(user)

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
