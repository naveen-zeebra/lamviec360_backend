# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/profile/controller.py
# Purpose : Orchestration layer for Platform Administrator Profile
# ─────────────────────────────────────────────────────────────────────────────

from typing import Dict, Any
from sqlalchemy.orm import Session
from shared.utils.logger import get_logger
from . import service
from .schemas import AdminProfileUpdate, AvatarUpdate

logger = get_logger("admin_profile_controller")


def get_admin_me_controller(user: Any) -> Dict[str, Any]:
    """Retrieve details for current admin."""
    return service.serialize_admin_user(user)


def update_admin_me_controller(data: AdminProfileUpdate, user: Any, db: Session) -> Dict[str, Any]:
    """Update admin profile details."""
    updated = service.update_admin_profile(
        db=db,
        user=user,
        full_name=data.full_name,
        phone=data.phone,
        avatar_url=data.avatar_url,
    )
    return {
        "id": updated.id,
        "email": updated.email,
        "full_name": updated.full_name,
        "phone": updated.phone,
        "avatar": updated.avatar_url,
    }


def update_avatar_controller(data: AvatarUpdate, user: Any, db: Session) -> Dict[str, str]:
    """Update admin avatar URL."""
    url = service.update_admin_avatar_url(db, user, data.avatar_url)
    return {"avatar_url": url}
