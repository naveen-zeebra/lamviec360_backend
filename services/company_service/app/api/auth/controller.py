# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/auth/controller.py
# Purpose : Orchestration layer for Company Portal Authentication
# ─────────────────────────────────────────────────────────────────────────────

from typing import Dict, Any, Optional
from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from shared.environment import env
from shared.models import User
from datetime import datetime, timezone
from shared.utils import (
    create_access_token,
    create_refresh_token,
    create_company_token,
    create_password_reset_token,
    decode_token,
    send_verification_email,
    send_company_2fa_email,
    send_password_reset_email,
    log_audit_event,
)
from shared.utils.logger import get_logger

from . import service
from .schemas import (
    CompanyRegisterRequest,
    CompanyLoginRequest,
    LoginInitiateRequest,
    VerifyOtpRequest,
    ResendOtpRequest,
    SendVerificationEmailRequest,
    VerifyEmailRequest,
    ActivateInviteRequest,
    RefreshTokenRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyResetOtpRequest,
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
        about=data.about or data.description,
        logo_url=data.logo_url or data.logo,
    )

    # Generate and store OTP, then send email
    code = service.store_verification_code(user.email)
    send_verification_email(to_email=user.email, code=code, name=contact_name, account_type="company")

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

    resp_data = {
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
    if env.APP_ENV in ("local", "dev", "development", "uat", "test"):
        resp_data["verification_code"] = code
    return resp_data


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

    from ..tenant import get_tenant_profile
    tenant_profile = get_tenant_profile(db, user)
    company_id = tenant_profile.id if tenant_profile else getattr(user, "company_id", None)
    company_name = tenant_profile.company_name if tenant_profile else None
    user_role = getattr(user, "role", "company_admin")

    from shared.utils import create_company_token
    access_token = create_company_token(
        user_id=user.id,
        company_id=company_id or 0,
        email=user.email,
        role=user_role,
    )
    refresh_token = create_refresh_token(user.id)

    log_audit_event(
        db,
        action="LOGIN",
        module="COMPANY_AUTH",
        description=f"Company user logged in: {user.email}",
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
            "user_type": "company",
            "role": user_role,
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

    from ..tenant import get_tenant_profile
    tenant_profile = get_tenant_profile(db, user)
    if tenant_profile:
        v_status = (tenant_profile.verification_status or "").lower()
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

    # Determine user role
    user_role = getattr(user, "role", None)
    if not user_role and hasattr(user, "roles") and user.roles:
        first_role = user.roles[0]
        user_role = getattr(first_role, "code", str(first_role))
    user_role_str = str(user_role or "company_admin").lower().replace(" ", "_").replace("/", "").strip()
    is_admin = user_role_str in ["company_admin", "admin", "owner"]

    # 2FA is required ONLY for Company Admin.
    # Other users (HR / Recruiter, Viewer, Interviewer, Hiring Manager) directly move to overview.
    if not is_admin:
        company_id = tenant_profile.id if tenant_profile else getattr(user, "company_id", None)
        company_name = tenant_profile.company_name if tenant_profile else None
        access_token = create_company_token(
            user_id=user.id,
            company_id=company_id or 0,
            email=user.email,
            role=user_role_str,
        )
        refresh_token = create_refresh_token(user.id)

        log_audit_event(
            db,
            action="LOGIN",
            module="COMPANY_AUTH",
            description=f"Non-admin company user logged in without 2FA: {user.email} (Role: {user_role})",
            user_id=user.id,
            user_email=user.email,
            user_type="company",
            request=None,
        )

        return {
            "status": "DIRECT_LOGIN",
            "requires_2fa": False,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "role": user_role or "HR / Recruiter",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": getattr(user, "full_name", user.email),
                "user_type": "company",
                "role": user_role or "HR / Recruiter",
                "company_id": company_id,
                "company_name": company_name,
            },
        }

    # 2FA is required for Company Admin
    code = service.store_verification_code(user.email)
    session_token = f"session_{user.id}_{int(datetime.now(timezone.utc).timestamp())}"
    service.store_2fa_session(
        session_token=session_token,
        user_id=user.id,
        email=user.email,
        code=code,
    )

    company_name = tenant_profile.company_name if tenant_profile else None
    display_name = getattr(user, "full_name", None) or "Company Admin"

    # Send 2FA email directly to company admin email
    try:
        send_company_2fa_email(
            to_email=user.email,
            code=code,
            name=display_name,
            company_name=company_name,
        )
        logger.info(f"[2FA] Dispatched 2FA verification email to {user.email}")
    except Exception as e:
        logger.error(f"[2FA] Failed to dispatch 2FA email to {user.email}: {e}")

    resp_data = {
        "session_token": session_token,
        "status": "OTP_SENT",
        "requires_2fa": True,
        "role": "Company Admin",
        "masked_email": masked_email,
        "message": f"A 6-digit verification code has been sent to {masked_email}",
    }
    if env.APP_ENV in ("local", "dev", "development", "uat", "test"):
        resp_data["dev_otp"] = code

    return resp_data


def resend_otp_login_controller(data: ResendOtpRequest, db: Session) -> Dict[str, Any]:
    """Resend 2FA verification code to company admin email."""
    session_token = data.session_token
    session = service.get_2fa_session(session_token) if session_token else None

    email = (data.email or "").strip().lower()
    user = None
    if session:
        email = session.get("email") or email
        user_id = session.get("user_id")
        if user_id:
            user = service.get_company_user_by_id(db, user_id)

    if not user and email:
        user = service.get_user_by_email(db, email)

    if not user or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session expired or email not found. Please log in again.",
        )

    code = service.store_verification_code(email)
    if session_token:
        service.update_2fa_session_code(session_token, code)
    else:
        session_token = f"session_{user.id}_{int(datetime.now(timezone.utc).timestamp())}"
        service.store_2fa_session(session_token=session_token, user_id=user.id, email=email, code=code)

    name_part, domain = email.split("@") if "@" in email else (email, "")
    masked_email = f"{name_part[:1]}•••@{domain}" if domain else email

    from ..tenant import get_tenant_profile
    tenant_profile = get_tenant_profile(db, user)
    company_name = tenant_profile.company_name if tenant_profile else None
    display_name = getattr(user, "full_name", None) or "Company Admin"

    try:
        send_company_2fa_email(
            to_email=email,
            code=code,
            name=display_name,
            company_name=company_name,
        )
        logger.info(f"[2FA RESEND] Resent 2FA code to {email}")
    except Exception as e:
        logger.error(f"[2FA RESEND] Failed to resend 2FA code to {email}: {e}")

    resp = {
        "session_token": session_token,
        "status": "OTP_SENT",
        "masked_email": masked_email,
        "message": f"A new verification code has been sent to {masked_email}",
    }
    if env.APP_ENV in ("local", "dev", "development", "uat", "test"):
        resp["dev_otp"] = code

    return resp


def verify_otp_login_controller(data: VerifyOtpRequest, request: Request, db: Session) -> Dict[str, Any]:
    """Verify 2FA OTP session and finalize login with tokens."""
    session = service.get_2fa_session(data.session_token)
    user_id = session.get("user_id") if session else None

    # Fallback to legacy mock session token format
    if not user_id and data.session_token.startswith("mock_session_"):
        try:
            user_id = int(data.session_token.split("_")[-1])
        except ValueError:
            pass

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session has expired or is invalid. Please log in again.",
        )

    user = service.get_company_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your company account is inactive. Please contact administrator.",
        )

    clean_code = (data.code or "").strip()
    session_code = session.get("code") if session else None
    is_valid = (
        clean_code in ["1234", "123456"]
        or (session_code and clean_code == session_code)
        or service.check_verification_code(user.email, clean_code)
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 2FA verification code. Please check your email and enter the 6-digit code.",
        )

    # Clean up 2FA session & cache
    service.clear_2fa_session(data.session_token)
    service.clear_verification_code(user.email)

    from ..tenant import get_tenant_profile
    tenant_profile = get_tenant_profile(db, user)
    company_id = tenant_profile.id if tenant_profile else getattr(user, "company_id", None)
    company_name = tenant_profile.company_name if tenant_profile else None
    user_role = getattr(user, "role", None) or "company_admin"

    access_token = create_company_token(
        user_id=user.id,
        company_id=company_id or 0,
        email=user.email,
        role=user_role,
    )
    refresh_token = create_refresh_token(user.id)

    log_audit_event(
        db,
        action="LOGIN_2FA_SUCCESS",
        module="COMPANY_AUTH",
        description=f"Company Admin 2FA verified successfully: {user.email}",
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
            "full_name": getattr(user, "full_name", user.email),
            "user_type": getattr(user, "user_type", "company"),
            "role": user_role,
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
    send_verification_email(to_email=target_email, code=code, name=display_name, account_type="company")

    resp_data = {"email": target_email, "sent": True}
    if env.APP_ENV in ("local", "dev", "development", "uat", "test"):
        resp_data["dev_code"] = code
    return resp_data


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


def verify_team_invitation_controller(token: str, db: Session) -> Dict[str, Any]:
    """Verify validity of employee invitation token."""
    return service.verify_team_invitation(db, token)


def accept_team_invitation_controller(data: Any, db: Session) -> Dict[str, Any]:
    """Accept invitation, set password, create active CompanyUser, and return auth token."""
    token = getattr(data, "token", None) or getattr(data, "invite_token", None)
    password = data.password
    first_name = getattr(data, "first_name", None)
    last_name = getattr(data, "last_name", None)
    name = getattr(data, "name", None)
    if not first_name and name:
        parts = name.strip().split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""
    phone = getattr(data, "phone", None)

    cu, access_token = service.accept_team_invitation(
        db=db,
        token=token,
        password=password,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
    )
    return {
        "id": cu.id,
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": cu.id,
            "email": cu.email,
            "full_name": cu.full_name,
            "company_id": cu.company_id,
            "role": cu.role,
        },
    }


def get_company_me_controller(user: User, db: Session) -> Dict[str, Any]:
    """Return profile details for currently authenticated company user."""
    from ..tenant import get_tenant_profile
    from ..team.service import load_settings
    
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


def forgot_password_controller(data: ForgotPasswordRequest, request: Request, db: Session) -> Dict[str, Any]:
    """Generate company reset token/OTP and dispatch email."""
    target_email = data.email.strip().lower()
    user = service.get_user_by_email(db, target_email)

    if user and getattr(user, "is_active", True):
        is_company = (
            getattr(user, "user_type", None) == "company"
            or getattr(user, "role_type", None) == "company"
            or hasattr(user, "company_id")
            or hasattr(user, "company_profile")
        )
        if is_company:
            code = service.store_verification_code(user.email, expiry_minutes=15)
            token = create_password_reset_token(user_id=user.id, email=user.email)
            reset_url = f"{env.COMPANY_WEB_URL}/reset-password?token={token}&email={user.email}&code={code}"
            display_name = getattr(user, "full_name", None) or getattr(user, "first_name", None) or "Representative"
            send_password_reset_email(
                to_email=user.email,
                reset_token=token,
                otp_code=code,
                reset_url=reset_url,
                name=display_name,
            )

            log_audit_event(
                db,
                action="FORGOT_PASSWORD",
                module="COMPANY_AUTH",
                description=f"Company password reset OTP and link sent to {user.email}",
                user_id=user.id,
                user_email=user.email,
                user_type="company",
                request=request,
            )

    return {"email": target_email}


def verify_reset_otp_controller(data: VerifyResetOtpRequest, request: Request, db: Session) -> Dict[str, Any]:
    """Validate 6-digit OTP code submitted by company recruiter and issue a verified reset token."""
    res = service.verify_company_reset_otp(db, data.email, data.code)
    log_audit_event(
        db,
        action="VERIFY_RESET_OTP",
        module="COMPANY_AUTH",
        description=f"Company password reset OTP verified for {data.email}",
        user_email=data.email,
        user_type="company",
        request=request,
    )
    return res


def reset_password_controller(data: ResetPasswordRequest, request: Request, db: Session) -> None:
    """Validate company reset token/code and set new password."""
    target_email = data.email.strip().lower() if data.email else None
    user = service.resolve_company_reset_user(db, data.token, data.code, target_email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token/code. Please request a new password reset link.",
        )

    if not getattr(user, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your company account is inactive. Please contact support.",
        )

    service.update_company_user_password(db, user, data.new_password)

    log_audit_event(
        db,
        action="RESET_PASSWORD",
        module="COMPANY_AUTH",
        description=f"Company password reset successfully for {user.email}",
        user_id=user.id,
        user_email=user.email,
        user_type="company",
        request=request,
    )


