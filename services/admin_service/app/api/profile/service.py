# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/profile/service.py
# Purpose : Domain & persistence logic for Platform Administrator Profile
# ─────────────────────────────────────────────────────────────────────────────

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from shared.models import User, AdminUser
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("admin_profile_service")


def serialize_admin_user(user: Any) -> Dict[str, Any]:
    """Compile roles, permissions, and profile details for admin user."""
    # Check if AdminUser or standard User
    if hasattr(user, "permissions_dict"):
        roles = user.roles
        role_codes = [r.code for r in roles] if hasattr(roles[0], "code") else [str(r) for r in roles]
        role_title = user.role_name or (roles[0].name if hasattr(roles[0], "name") else "Super Admin")
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "name": user.full_name,
            "phone": user.phone,
            "avatar": user.avatar_url,
            "avatar_url": user.avatar_url,
            "role": role_title,
            "roles": role_codes,
            "permissions": user.permissions_dict,
            "user_type": user.user_type,
            "is_superuser": user.is_superuser,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }

    # Standard User fallback
    roles = [r.name for r in user.roles]
    role_codes = [r.code for r in user.roles]
    permissions = []
    for r in user.roles:
        for p in r.permissions:
            permissions.append(f"{p.module}:{p.action}")

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "name": user.full_name,
        "phone": user.phone,
        "avatar": user.avatar_url,
        "avatar_url": user.avatar_url,
        "role": roles[0] if roles else "Super Admin",
        "roles": role_codes,
        "permissions": list(set(permissions)),
        "user_type": user.user_type,
        "is_superuser": user.is_superuser,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@service_error_handler
def update_admin_profile(
    db: Session,
    user: Any,
    full_name: Optional[str] = None,
    phone: Optional[str] = None,
    avatar_url: Optional[str] = None,
) -> Any:
    """Update admin entity profile fields."""
    if full_name:
        user.full_name = full_name
    if phone is not None:
        user.phone = phone
    if avatar_url is not None:
        user.avatar_url = avatar_url

    db.commit()
    db.refresh(user)
    logger.info(f"Updated admin profile for id={user.id}")
    return user


@service_error_handler
def update_admin_avatar_url(db: Session, user: Any, avatar_url: str) -> str:
    """Update avatar URL for admin."""
    user.avatar_url = avatar_url
    db.commit()
    db.refresh(user)
    logger.info(f"Updated avatar for admin id={user.id}")
    return user.avatar_url
