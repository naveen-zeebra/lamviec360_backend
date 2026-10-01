# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/auth/controller.py
# Purpose : Orchestration layer for Admin Portal Authentication
# ─────────────────────────────────────────────────────────────────────────────

from datetime import datetime, timedelta
from typing import Dict, Any
from fastapi import BackgroundTasks, HTTPException, Request, status
from sqlalchemy.orm import Session

from shared.environment import env
from shared.utils.jwt import (
    create_access_token,
    create_admin_token,
    create_refresh_token,
    decode_token,
)
from shared.utils.audit import log_audit_event
from shared.utils.email import send_password_reset_email
from shared.utils.logger import get_logger

from . import service
from .schemas import (
    AdminLoginRequest,
    RefreshTokenRequest,
    LogoutRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)

logger = get_logger("admin_auth_controller")


def admin_login_controller(data: AdminLoginRequest, request: Request, db: Session) -> Dict[str, Any]:
    """Authenticate administrator, issue access/refresh tokens, and audit login."""
    logger.info(f"Admin login attempt for {data.email}")
    user = service.admin_login_user(db, data.email, data.password)
    if not user:
        logger.warning(f"Admin login failed: invalid credentials for {data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
        )

    user_id = user["id"]
    email = user["email"]
    roles = user.get("roles", [])
    user_type = user.get("user_type", "super_admin")
    permissions = user.get("permissions", [])

    access_token = create_admin_token(
        admin_id=user_id,
        email=email,
        role_code=roles[0] if roles else "super_admin",
        permissions=permissions,
    )

    refresh_token = create_refresh_token(user_id)
    refresh_expires_at = datetime.utcnow() + timedelta(days=env.REFRESH_TOKEN_EXPIRE_DAYS)
    service.save_refresh_token(db, user_id, refresh_token, refresh_expires_at)

    logger.info(f"Admin login successful for {data.email}")
    log_audit_event(
        db,
        action="ADMIN_LOGIN",
        module="ADMIN_AUTH",
        description=f"Admin logged in: {email} ({user.get('role', 'Administrator')})",
        user_id=user_id,
        user_email=email,
        user_type=user_type,
        request=request,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": env.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": str(user["id"]),
            "email": user["email"],
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
            "name": user.get("full_name"),
            "full_name": user.get("full_name"),
            "role": user.get("role"),
            "roles": user.get("roles"),
            "permissions": user.get("permissions_dict") or user.get("permissions"),
            "avatar": user.get("avatar"),
            "avatar_url": user.get("avatar"),
        },
    }


def refresh_token_controller(data: RefreshTokenRequest, db: Session) -> Dict[str, Any]:
    """Validate refresh token from DB and payload, issue new access token, and rotate refresh token."""
    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token type, refresh token expected",
        )

    # Validate active token record in database
    record = service.get_valid_refresh_token(db, data.refresh_token)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid or expired. Please login again.",
        )

    admin_id = int(payload.get("sub", 0))
    user = service.get_admin_with_permissions(db, admin_id)
    if not user or not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin account not found or is inactive",
        )

    # Issue fresh access token
    access_token = create_admin_token(
        admin_id=user["id"],
        email=user["email"],
        role_code=user.get("roles", ["super_admin"])[0],
        permissions=user.get("permissions", []),
    )

    # Rotate refresh token: revoke current and issue new
    service.revoke_refresh_token(db, data.refresh_token)
    new_refresh_token = create_refresh_token(user["id"])
    new_expires_at = datetime.utcnow() + timedelta(days=env.REFRESH_TOKEN_EXPIRE_DAYS)
    service.save_refresh_token(db, user["id"], new_refresh_token, new_expires_at)

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": env.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


def logout_controller(data: LogoutRequest, db: Session) -> Dict[str, str]:
    """Revoke the current refresh token."""
    service.revoke_refresh_token(db, data.refresh_token)
    return {"message": "Logged out successfully"}


def logout_all_controller(admin_id: int, db: Session) -> Dict[str, str]:
    """Revoke all active refresh tokens for the administrator across all sessions/devices."""
    service.revoke_all_admin_tokens(db, admin_id)
    return {"message": "Logged out from all devices"}


def forgot_password_controller(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session,
) -> Dict[str, str]:
    """Generate reset token and dispatch password reset email via background task."""
    result = service.create_password_reset_token(db, data.email)
    logger.info(f"[ForgotPassword] Request for {data.email} | matched={bool(result)}")

    if result:
        background_tasks.add_task(
            send_password_reset_email,
            to_email=result["email"],
            reset_token=result["reset_token"],
            reset_url=result["reset_link"],
            name=result["first_name"],
        )

    # Always return a uniform response to prevent account enumeration
    return {"message": "If the account exists, a password reset link has been dispatched."}


def reset_password_controller(data: ResetPasswordRequest, db: Session) -> Dict[str, str]:
    """Validate token and reset password."""
    success = service.reset_password_with_token(db, data.token, data.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset link is invalid or has expired. Please request a new one.",
        )
    return {"message": "Password reset successfully. You can now log in with your new password."}


def change_password_controller(
    data: ChangePasswordRequest,
    current_user: Any,
    db: Session,
) -> Dict[str, str]:
    """Change the current administrator's password after verifying the current password."""
    old_password = data.old_password or data.current_password
    if old_password == data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )

    admin_id = current_user.id
    success = service.change_admin_password(db, admin_id, old_password, data.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    return {"message": "Admin password updated successfully"}
