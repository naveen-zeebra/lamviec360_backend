# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/auth/controller.py
# Purpose : Orchestration layer for Job Seeker Authentication
# ─────────────────────────────────────────────────────────────────────────────

from typing import Dict, Any, Optional, List
from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from shared.models import User
from shared.utils import (
    create_access_token,
    create_jobseeker_token,
    create_refresh_token,
    create_password_reset_token,
    decode_token,
    log_audit_event,
    send_verification_email,
    send_password_reset_email,
)
from shared.utils.logger import get_logger

from . import service
from .schemas import (
    JobSeekerRegisterRequest,
    JobSeekerLoginRequest,
    RefreshTokenRequest,
    ChangePasswordRequest,
    SendVerificationEmailRequest,
    VerifyEmailRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    OAuthLoginRequest,
    GoogleLoginRequest,
    ZaloLoginRequest,
    LinkedInLoginRequest,
    FacebookLoginRequest,
)

logger = get_logger("jobseeker_auth_controller")


def register_jobseeker_controller(data: JobSeekerRegisterRequest, request: Request, db: Session) -> Dict[str, Any]:
    """Register candidate, issue tokens, send verification OTP."""
    # BR-101-01 & BR-101-06: Email and Phone must be unique for active accounts
    existing_email = service.get_user_by_email(db, data.email)
    if existing_email and not existing_email.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An active account with this email address already exists.",
        )

    if data.phone and str(data.phone).strip():
        clean_phone = str(data.phone).strip()
        existing_phone = (
            db.query(User)
            .filter(
                User.phone == clean_phone,
                User.is_deleted == False,
                User.is_active == True,
            )
            .first()
        )
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An active account with this phone number already exists",
            )

    user, _ = service.create_jobseeker_user(
        db=db,
        email=data.email,
        password=data.password,
        full_name=data.full_name,
        phone=data.phone,
    )

    code = service.store_verification_code(user.email)
    try:
        send_verification_email(to_email=user.email, code=code, name=user.full_name)
    except Exception as e:
        logger.warning(f"Verification email sending failed: {e}")

    access_token = create_jobseeker_token(
        seeker_id=user.id,
        email=user.email,
    )
    refresh_token = create_refresh_token(user.id)

    log_audit_event(
        db,
        action="REGISTER",
        module="JOBSEEKER_AUTH",
        description=f"New jobseeker registered: {user.email}",
        user_id=user.id,
        user_email=user.email,
        user_type="jobseeker",
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
        },
    }


def login_jobseeker_controller(data: JobSeekerLoginRequest, request: Request, db: Session) -> Dict[str, Any]:
    """Authenticate jobseeker and issue tokens."""
    user = service.authenticate_jobseeker(db, data.email, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if user.role_type != "jobseeker":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Please login via the job seeker portal.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact support.",
        )

    # BR-101-08: Update last_login timestamp and unarchive active candidate if previously archived
    from datetime import datetime, timezone
    user.last_login = datetime.now(timezone.utc)
    if user.jobseeker_profile and getattr(user.jobseeker_profile, "is_archived", False):
        user.jobseeker_profile.is_archived = False
        user.jobseeker_profile.archived_at = None
        user.jobseeker_profile.archive_reason = None
        user.jobseeker_profile.is_visible = True
    db.commit()

    access_token = create_jobseeker_token(
        seeker_id=user.id,
        email=user.email,
    )
    refresh_token = create_refresh_token(user.id)

    log_audit_event(
        db,
        action="LOGIN",
        module="JOBSEEKER_AUTH",
        description=f"Jobseeker logged in: {user.email}",
        user_id=user.id,
        user_email=user.email,
        user_type=user.user_type,
        request=request,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "id": user.id,
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "name": user.full_name,
        "role": user.role_type,
        "email_verified": user.is_verified,
        "user": {
            "id": user.id,
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "name": user.full_name,
            "user_type": user.user_type,
            "role": user.role_type,
            "avatar_url": user.avatar_url,
        },
    }


def get_me_controller(user: User) -> Dict[str, Any]:
    """Fetch current jobseeker user profile."""
    profile_data = None
    if user.jobseeker_profile:
        p = user.jobseeker_profile
        profile_data = {
            "id": p.id,
            "headline": p.headline,
            "bio": p.bio,
            "skills": p.skills,
            "experience_years": float(p.experience_years or 0),
            "expected_salary": float(p.expected_salary) if p.expected_salary else None,
            "resume_url": p.resume_url,
            "city": p.city,
            "country": p.country,
            "github_url": p.github_url,
            "linkedin_url": p.linkedin_url,
        }
    return {
        "id": user.id,
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "name": user.full_name,
        "phone": user.phone,
        "avatar_url": user.avatar_url,
        "user_type": user.user_type,
        "role": user.role_type,
        "is_verified": user.is_verified,
        "email_verified": user.is_verified,
        "profile": profile_data,
    }


def refresh_token_controller(data: RefreshTokenRequest, db: Session) -> Dict[str, Any]:
    """Refresh access token."""
    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token type")

    user_id = payload.get("sub")
    user = service.get_user_by_id(db, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not active")

    roles = [r.code for r in user.roles] or ["jobseeker"]
    new_access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        user_type=user.user_type,
        roles=roles,
    )
    return {"access_token": new_access_token, "token_type": "bearer"}


def change_password_controller(data: ChangePasswordRequest, user: User, db: Session) -> None:
    """Change candidate password."""
    success = service.change_password(db, user, data.old_password, data.new_password)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")


def send_verification_email_controller(
    data: Optional[SendVerificationEmailRequest],
    current_user: Optional[User],
    db: Session,
) -> Dict[str, Any]:
    """Dispatch verification email code."""
    target_email = ((data.email or "") if data else "").strip().lower()
    if not target_email and current_user:
        target_email = current_user.email.strip().lower()

    if not target_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is required to send verification code",
        )

    user = service.get_user_by_email(db, target_email)
    display_name = user.full_name if user else (current_user.full_name if current_user else "Job Seeker")

    code = service.store_verification_code(target_email)
    send_verification_email(to_email=target_email, code=code, name=display_name)
    return {"email": target_email}


def verify_email_controller(
    data: VerifyEmailRequest,
    request: Request,
    current_user: Optional[User],
    db: Session,
) -> Dict[str, Any]:
    """Validate OTP code and mark candidate email verified."""
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
    user = service.mark_jobseeker_verified(db, target_email)
    if user:
        log_audit_event(
            db,
            action="VERIFY_EMAIL",
            module="JOBSEEKER_AUTH",
            description=f"Jobseeker verified email: {user.email}",
            user_id=user.id,
            user_email=user.email,
            user_type=user.user_type,
            request=request,
        )

    access_token = create_jobseeker_token(seeker_id=user.id, email=user.email) if user else None
    return {
        "email": target_email,
        "is_verified": True,
        "access_token": access_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
        } if user else None,
    }


def forgot_password_controller(data: ForgotPasswordRequest, request: Request, db: Session) -> Dict[str, Any]:
    """Generate reset token and dispatch email."""
    target_email = data.email.strip().lower()
    user = service.get_user_by_email(db, target_email)

    if user and user.is_active:
        token = create_password_reset_token(user_id=user.id, email=user.email)
        service.store_verification_code(target_email, expiry_minutes=60)
        send_password_reset_email(to_email=user.email, reset_token=token, name=user.full_name)

        log_audit_event(
            db,
            action="FORGOT_PASSWORD",
            module="JOBSEEKER_AUTH",
            description=f"Password reset link sent to {user.email}",
            user_id=user.id,
            user_email=user.email,
            user_type=user.user_type,
            request=request,
        )

    return {"email": target_email}


def reset_password_controller(data: ResetPasswordRequest, request: Request, db: Session) -> None:
    """Validate reset token/code and set new password."""
    target_email = data.email.strip().lower() if data.email else None
    user = service.resolve_reset_user(db, data.token, data.code, target_email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token/code. Please request a new password reset link.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    service.update_user_password(db, user, data.new_password)

    log_audit_event(
        db,
        action="RESET_PASSWORD",
        module="JOBSEEKER_AUTH",
        description=f"Password reset successfully for {user.email}",
        user_id=user.id,
        user_email=user.email,
        user_type=user.user_type,
        request=request,
    )


def oauth_login_controller(data: OAuthLoginRequest, request: Request, db: Session) -> Dict[str, Any]:
    """
    Authenticate or register candidate via OAuth (Google, Zalo, LinkedIn, Facebook).
    Supports LV-BR-0037 auto-linking to existing accounts.
    """
    provider = data.provider.lower()

    # 1. Resolve and verify OAuth credentials & profile
    oauth_info = service.verify_oauth_credentials(
        provider=provider,
        code=data.code,
        token=data.token,
        redirect_uri=data.redirect_uri,
        code_verifier=data.code_verifier,
        fallback_email=data.email,
        fallback_name=data.name,
        fallback_avatar=data.avatar_url,
        fallback_id=data.provider_user_id,
    )

    # 2. Authenticate or create user in database
    user, is_new_user, is_auto_linked = service.authenticate_or_register_oauth_user(db, oauth_info)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Please contact support.",
        )

    # 3. Issue authentication JWT tokens
    access_token = create_jobseeker_token(seeker_id=user.id, email=user.email)
    refresh_token = create_refresh_token(user.id)

    # 4. Log audit event
    action_type = "OAUTH_REGISTER" if is_new_user else ("OAUTH_AUTO_LINK" if is_auto_linked else "OAUTH_LOGIN")
    description = (
        f"Registered new jobseeker via {provider} ({user.email})"
        if is_new_user
        else (
            f"Auto-linked {provider} account to existing user ({user.email}) per LV-BR-0037"
            if is_auto_linked
            else f"Jobseeker logged in via {provider} ({user.email})"
        )
    )

    log_audit_event(
        db,
        action=action_type,
        module="JOBSEEKER_AUTH",
        description=description,
        user_id=user.id,
        user_email=user.email,
        user_type="jobseeker",
        request=request,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "is_new_user": is_new_user,
        "is_auto_linked": is_auto_linked,
        "provider": provider,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
            "user_type": user.user_type,
            "is_verified": user.is_verified,
        },
    }


def get_oauth_url_controller(provider: str, redirect_uri: Optional[str] = None, state: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve official authorization redirect URL for an OAuth provider."""
    return service.get_oauth_authorization_url(provider=provider, redirect_uri=redirect_uri, state=state)


def get_oauth_providers_controller() -> List[Dict[str, Any]]:
    """Retrieve list of supported OAuth providers."""
    return service.get_oauth_providers_config()
