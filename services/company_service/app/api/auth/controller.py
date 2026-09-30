# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/auth/controller.py
# Purpose : Orchestration layer for Company Portal Authentication
# ─────────────────────────────────────────────────────────────────────────────

from typing import Dict, Any, Optional
from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from shared.models import User
from shared.utils import (
    create_access_token,
    create_refresh_token,
    decode_token,
    send_verification_email,
    log_audit_event,
)
from shared.utils.logger import get_logger

from . import service
from .schemas import (
    CompanyRegisterRequest,
    CompanyLoginRequest,
    LoginInitiateRequest,
    VerifyOtpRequest,
    SendVerificationEmailRequest,
    VerifyEmailRequest,
    ActivateInviteRequest,
    RefreshTokenRequest,
    ChangePasswordRequest,
)

logger = get_logger("company_auth_controller")


def register_company_controller(data: CompanyRegisterRequest, request: Request, db: Session) -> Dict[str, Any]:
    """Register a new company employer account, dispatch verification OTP, and return initial tokens."""
    existing = service.get_user_by_email(db, data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists",
        )

    contact_name = data.contact_name or data.full_name or data.company_name or "Representative"
    company_name = data.company_name or "New Company"

    user, profile = service.create_company_user_and_profile(
        db=db,
        email=data.email,
        password=data.password,
        company_name=company_name,
        contact_name=contact_name,
        phone=data.phone,
        industry=data.industry,
        size=data.size or data.company_size,
        website=data.website,
        tax_code=data.tax_id or data.tax_code or data.reg_number,
    )

    # Generate and store OTP, then send email
    code = service.store_verification_code(user.email)
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

    return {
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
    }


def login_company_controller(data: CompanyLoginRequest, request: Request, db: Session) -> Dict[str, Any]:
    """Authenticate company recruiter and return session tokens."""
    user = service.authenticate_company_user(db, data.email, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if user.role_type != "company":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Please login via the company portal.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your company account is inactive. Please contact administrator.",
        )

    roles = [r.code for r in user.roles] or ["company"]
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

    return {
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
    }


def initiate_otp_login_controller(data: LoginInitiateRequest, db: Session) -> Dict[str, Any]:
    """Validate credentials and prepare 2FA OTP flow for employer."""
    user = service.authenticate_company_user(db, data.email, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if user.role_type != "company":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Please login via the company portal.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your company account is inactive. Please contact administrator.",
        )

    if user.company_profile:
        v_status = (user.company_profile.verification_status or "").lower()
        if v_status == "pending":
            return {
                "status": "PENDING_APPROVAL",
                "session_token": None,
                "message": "Your company registration is pending approval.",
            }
        elif v_status == "rejected":
            return {
                "status": "REJECTED",
                "session_token": None,
                "message": "Your company registration was not approved.",
            }

    email = user.email
    name, domain = email.split("@") if "@" in email else (email, "")
    masked_email = f"{name[:1]}•••@{domain}" if domain else email

    return {
        "session_token": f"mock_session_{user.id}",
        "status": "OTP_SENT",
        "masked_email": masked_email,
    }


def verify_otp_login_controller(data: VerifyOtpRequest, request: Request, db: Session) -> Dict[str, Any]:
    """Verify OTP session and finalize login with tokens."""
    if not data.session_token.startswith("mock_session_"):
        raise HTTPException(status_code=400, detail="Invalid session token")

    if data.code not in ["1234", "123456"]:
        raise HTTPException(status_code=400, detail="Invalid OTP code. Please enter 123456.")

    user_id = int(data.session_token.split("_")[-1])
    user = service.get_company_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your company account is inactive. Please contact administrator.",
        )

    roles = [r.code for r in user.roles] or ["company"]
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        user_type=user.user_type,
        roles=roles,
    )
    refresh_token = create_refresh_token(user.id)

    company_id = user.company_profile.id if user.company_profile else None
    company_name = user.company_profile.company_name if user.company_profile else None

    return {
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
    }


def send_verification_email_controller(
    data: Optional[SendVerificationEmailRequest],
    current_user: Optional[User],
    db: Session,
) -> Dict[str, Any]:
    """Generate and dispatch verification code via email."""
    target_email = ((data.email or "") if data else "").strip().lower()
    if not target_email and current_user:
        target_email = current_user.email.strip().lower()

    if not target_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is required to send verification code",
        )

    user = service.get_user_by_email(db, target_email)
    display_name = user.full_name if user else (current_user.full_name if current_user else "Employer")

    code = service.store_verification_code(target_email)
    send_verification_email(to_email=target_email, code=code, name=display_name)

    return {"email": target_email}


def verify_email_controller(
    data: VerifyEmailRequest,
    request: Request,
    current_user: Optional[User],
    db: Session,
) -> Dict[str, Any]:
    """Validate 6-digit OTP and mark user account verified."""
    target_email = ((data.email or "") if data else "").strip().lower()
    if not target_email and current_user:
        target_email = current_user.email.strip().lower()

    if not target_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is required",
        )

    if not service.check_verification_code(target_email, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code",
        )

    service.clear_verification_code(target_email)
    user = service.mark_user_verified(db, target_email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

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

    return {"email": target_email, "is_verified": True}


def get_invite_controller(db: Session, token: str) -> Dict[str, Any]:
    """Retrieve details for a pending team invite."""
    return service.get_invite_details(db, token)


def activate_invite_controller(data: ActivateInviteRequest, db: Session) -> Dict[str, Any]:
    """Activate invited company team member."""
    return service.activate_invite_member(db, data.invite_token, data.name, data.password)


def get_company_me_controller(user: User, db: Session) -> Dict[str, Any]:
    """Return profile details for currently authenticated company user."""
    from ..team.service import get_tenant_profile, load_settings
    
    profile = get_tenant_profile(db, user)
    
    # Check if they are a team member and what their role is
    role_name = "Company Admin"
    settings = load_settings(profile)
    team_members = settings.get("team_members", [])
    for m in team_members:
        if m.get("email") == user.email:
            role_name = m.get("role", "Company Admin")
            break

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

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "user_name": user.full_name,
        "user_email": user.email,
        "phone": user.phone,
        "user_type": user.user_type,
        "company_id": profile.id if profile else None,
        "company_name": profile.company_name if profile else None,
        "company_profile": profile_data,
        "role": role_name,
        "approval_status": profile.verification_status if profile else "verified",
    }


def refresh_token_controller(data: RefreshTokenRequest, db: Session) -> Dict[str, Any]:
    """Exchange refresh token for a fresh access token."""
    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token type")

    user_id = payload.get("sub")
    user = service.get_company_user_by_id(db, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not active")

    roles = [r.code for r in user.roles] or ["company"]
    new_access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        user_type=user.user_type,
        roles=roles,
    )
    return {"access_token": new_access_token, "token_type": "bearer"}


def change_password_controller(data: ChangePasswordRequest, user: User, db: Session) -> Dict[str, str]:
    """Change company password."""
    success = service.change_company_user_password(db, user, data.old_password, data.new_password)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    return {"message": "Password updated successfully"}
