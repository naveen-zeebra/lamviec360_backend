# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/auth/service.py
# Purpose : Authentication domain & persistence logic for Admin Portal
# ─────────────────────────────────────────────────────────────────────────────

from datetime import datetime, timedelta
import secrets
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from shared.environment import env
from shared.models import AdminUser, AdminRole, AdminRefreshToken, AdminPasswordReset, User
from shared.utils.error_handler import service_error_handler
from shared.utils.password import hash_password, verify_password
from shared.utils.logger import get_logger

logger = get_logger("admin_auth_service")

RESET_TOKEN_EXPIRY_MINUTES = 30


@service_error_handler
def admin_login_user(db: Session, email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate an administrator using AdminUser table (with fallback to User table).
    Returns admin details dictionary with roles and permissions, or None.
    """
    # 1. Check dedicated AdminUser table first
    admin = db.query(AdminUser).filter(
        AdminUser.email == email.lower(),
        AdminUser.is_deleted == False,
    ).first()

    if admin and verify_password(password, admin.password_hash):
        if not admin.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin account is inactive",
            )

        role_code = admin.role_rel.code if admin.role_rel else "super_admin"
        permissions: List[str] = []
        if admin.role_rel:
            for p in admin.role_rel.permissions:
                actions = []
                if p.can_view:
                    actions.append("view")
                if p.can_create:
                    actions.append("create")
                if p.can_edit:
                    actions.append("edit")
                if p.can_delete:
                    actions.append("delete")
                permissions.append(f"{p.module_key.lower()}:{','.join(actions)}")

        admin.last_login = datetime.utcnow()
        db.commit()

        return {
            "id": admin.id,
            "email": admin.email,
            "first_name": admin.first_name,
            "last_name": admin.last_name,
            "full_name": admin.full_name,
            "role": admin.role_name,
            "roles": [role_code],
            "role_code": role_code,
            "user_type": admin.user_type,
            "permissions": permissions,
            "permissions_dict": admin.permissions_dict,
            "avatar": admin.avatar_url,
            "is_superuser": admin.is_superuser,
        }

    # 2. Fallback check for legacy administrative accounts in User table
    user = db.query(User).filter(
        User.email == email.lower(),
        User.is_deleted == False,
    ).first()

    if not user or not verify_password(password, user.hashed_password):
        return None

    is_admin = user.is_superuser or user.user_type in ["super_admin", "admin"]
    if not is_admin:
        role_codes = [r.code for r in user.roles]
        if not any(code in ["super_admin", "admin"] for code in role_codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access restricted to administrative staff only",
            )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is inactive",
        )

    roles = [r.code for r in user.roles] or [user.user_type]
    permissions = []
    for r in user.roles:
        for p in r.permissions:
            permissions.append(f"{p.module}:{p.action}")

    user.last_login = datetime.utcnow()
    db.commit()

    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.full_name,
        "role": roles[0] if roles else "admin",
        "roles": roles,
        "role_code": roles[0] if roles else "admin",
        "user_type": user.user_type,
        "permissions": list(set(permissions)),
        "permissions_dict": {},
        "avatar": user.avatar_url,
        "is_superuser": user.is_superuser,
    }


@service_error_handler
def get_admin_with_permissions(db: Session, admin_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve full admin record with roles and permissions by ID."""
    admin = db.query(AdminUser).filter(
        AdminUser.id == admin_id,
        AdminUser.is_deleted == False,
    ).first()

    if admin:
        role_code = admin.role_rel.code if admin.role_rel else "super_admin"
        permissions: List[str] = []
        if admin.role_rel:
            for p in admin.role_rel.permissions:
                actions = []
                if p.can_view:
                    actions.append("view")
                if p.can_create:
                    actions.append("create")
                if p.can_edit:
                    actions.append("edit")
                if p.can_delete:
                    actions.append("delete")
                permissions.append(f"{p.module_key.lower()}:{','.join(actions)}")

        return {
            "id": admin.id,
            "email": admin.email,
            "first_name": admin.first_name,
            "last_name": admin.last_name,
            "full_name": admin.full_name,
            "role": admin.role_name,
            "roles": [role_code],
            "role_code": role_code,
            "user_type": admin.user_type,
            "permissions": permissions,
            "permissions_dict": admin.permissions_dict,
            "avatar": admin.avatar_url,
            "is_active": admin.is_active,
        }

    # Fallback to User table
    user = db.query(User).filter(
        User.id == admin_id,
        User.is_deleted == False,
    ).first()

    if not user:
        return None

    roles = [r.code for r in user.roles] or [user.user_type]
    permissions = []
    for r in user.roles:
        for p in r.permissions:
            permissions.append(f"{p.module}:{p.action}")

    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.full_name,
        "role": roles[0] if roles else "admin",
        "roles": roles,
        "role_code": roles[0] if roles else "admin",
        "user_type": user.user_type,
        "permissions": list(set(permissions)),
        "permissions_dict": {},
        "avatar": user.avatar_url,
        "is_active": user.is_active,
    }


@service_error_handler
def save_refresh_token(db: Session, admin_id: int, token: str, expires_at: datetime) -> None:
    """Store refresh token and delete expired tokens for this administrator."""
    now = datetime.utcnow()
    db.query(AdminRefreshToken).filter(
        AdminRefreshToken.admin_id == admin_id,
        AdminRefreshToken.expires_at <= now,
    ).delete()

    db.add(
        AdminRefreshToken(
            admin_id=admin_id,
            token=token,
            expires_at=expires_at,
            is_revoked=False,
        )
    )
    db.commit()
    logger.info(f"Admin refresh token saved for admin_id={admin_id}")


@service_error_handler
def get_valid_refresh_token(db: Session, token: str) -> Optional[AdminRefreshToken]:
    """Retrieve active and non-expired refresh token record."""
    return db.query(AdminRefreshToken).filter(
        AdminRefreshToken.token == token,
        AdminRefreshToken.is_revoked == False,
        AdminRefreshToken.expires_at > datetime.utcnow(),
    ).first()


@service_error_handler
def revoke_refresh_token(db: Session, token: str) -> bool:
    """Revoke a single refresh token upon logout."""
    record = db.query(AdminRefreshToken).filter(AdminRefreshToken.token == token).first()
    if not record:
        return False
    record.is_revoked = True
    db.commit()
    logger.info(f"Admin refresh token revoked for admin_id={record.admin_id}")
    return True


@service_error_handler
def revoke_all_admin_tokens(db: Session, admin_id: int) -> None:
    """Revoke all active refresh tokens for an administrator (logout all devices)."""
    db.query(AdminRefreshToken).filter(
        AdminRefreshToken.admin_id == admin_id,
        AdminRefreshToken.is_revoked == False,
    ).update({"is_revoked": True})
    db.commit()
    logger.info(f"All admin refresh tokens revoked for admin_id={admin_id}")


@service_error_handler
def create_password_reset_token(db: Session, email: str) -> Optional[Dict[str, Any]]:
    """
    Generate a secure 32-byte reset token with 30 minutes expiration.
    Returns token details dictionary for email dispatch, or None if admin not found.
    """
    admin = db.query(AdminUser).filter(
        AdminUser.email == email.lower(),
        AdminUser.is_deleted == False,
    ).first()

    user_fallback = None
    if not admin:
        user_fallback = db.query(User).filter(
            User.email == email.lower(),
            User.is_deleted == False,
        ).first()
        if not user_fallback or user_fallback.user_type not in ["super_admin", "admin"]:
            return None

    target_id = admin.id if admin else user_fallback.id
    first_name = (admin.first_name if admin else user_fallback.first_name) or "Administrator"
    target_email = admin.email if admin else user_fallback.email

    # Invalidate existing unused tokens for this admin
    db.query(AdminPasswordReset).filter(
        AdminPasswordReset.admin_id == target_id,
        AdminPasswordReset.is_used == False,
    ).update({"is_used": True})

    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)

    db.add(
        AdminPasswordReset(
            admin_id=target_id,
            token=token,
            expires_at=expires_at,
            is_used=False,
        )
    )
    db.commit()

    admin_panel_url = env.ADMIN_WEB_URL or "http://localhost:3002"
    reset_link = f"{admin_panel_url}/reset-password?token={token}&email={target_email}"

    logger.info(f"Password reset token generated for admin_id={target_id}")

    return {
        "admin_id": target_id,
        "first_name": first_name,
        "email": target_email,
        "reset_token": token,
        "reset_link": reset_link,
        "expiry_minutes": RESET_TOKEN_EXPIRY_MINUTES,
    }


@service_error_handler
def reset_password_with_token(db: Session, token: str, new_password: str) -> bool:
    """Validate reset token and update administrator password."""
    record = db.query(AdminPasswordReset).filter(
        AdminPasswordReset.token == token,
        AdminPasswordReset.is_used == False,
        AdminPasswordReset.expires_at > datetime.utcnow(),
    ).first()

    if not record:
        return False

    admin = db.query(AdminUser).filter(AdminUser.id == record.admin_id).first()
    if admin:
        admin.password_hash = hash_password(new_password)
    else:
        user = db.query(User).filter(User.id == record.admin_id).first()
        if user:
            user.hashed_password = hash_password(new_password)
        else:
            return False

    record.is_used = True
    db.commit()
    logger.info(f"Password reset completed for admin_id={record.admin_id}")
    return True


@service_error_handler
def change_admin_password(db: Session, admin_id: int, old_password: str, new_password: str) -> bool:
    """Verify old password and update to new password for authenticated admin."""
    admin = db.query(AdminUser).filter(AdminUser.id == admin_id).first()
    if admin:
        if not verify_password(old_password, admin.password_hash):
            return False
        admin.password_hash = hash_password(new_password)
        db.commit()
        logger.info(f"Password changed for AdminUser id={admin_id}")
        return True

    user = db.query(User).filter(User.id == admin_id).first()
    if user:
        if not verify_password(old_password, user.hashed_password):
            return False
        user.hashed_password = hash_password(new_password)
        db.commit()
        logger.info(f"Password changed for User id={admin_id}")
        return True

    return False
