# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/admin_users/controller.py
# Purpose : Orchestration layer for Platform Administrator Management
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session

from shared.models import User
from shared.utils import log_audit_event
from shared.utils.logger import get_logger
from .schemas import AdminUserCreateSchema, AdminUserUpdateSchema
from .service import (
    get_all_admin_roles,
    query_admin_users,
    get_admin_user_by_id,
    get_admin_user_by_email,
    create_admin_user_record,
    update_admin_user_record,
    toggle_admin_user_active_state,
    serialize_admin_user_item,
)

logger = get_logger("admin_users_controller")


def list_admin_roles_controller(db: Session) -> List[Dict[str, Any]]:
    """Return all administrator roles with their permission maps."""
    return get_all_admin_roles(db)


def list_admin_users_controller(
    db: Session,
    search: Optional[str] = None,
    role: Optional[str] = None,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieve filtered and paginated administrator accounts."""
    return query_admin_users(
        db=db,
        search=search,
        role=role,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )


def get_admin_user_detail_controller(db: Session, admin_id: int) -> Dict[str, Any]:
    """Fetch complete detail of an administrator."""
    a = get_admin_user_by_id(db, admin_id)
    if not a:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Platform administrator with ID {admin_id} not found",
        )
    return serialize_admin_user_item(a)


def create_admin_user_controller(
    db: Session,
    data: AdminUserCreateSchema,
    current_admin: User,
    request: Optional[Request] = None,
) -> Dict[str, Any]:
    """Create a new platform administrator account."""
    existing = get_admin_user_by_email(db, data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An administrator account with this email already exists",
        )

    new_admin = create_admin_user_record(db, data.model_dump())

    log_audit_event(
        db,
        action="CREATE_ADMIN_USER",
        module="ADMIN_MANAGEMENT",
        description=f"Super Admin {current_admin.email} created platform admin {new_admin.email} ({new_admin.role_name})",
        user_id=current_admin.id,
        user_email=current_admin.email,
        user_type="super_admin",
        request=request,
    )

    return {
        "id": str(new_admin.id),
        "email": new_admin.email,
        "name": new_admin.full_name,
        "role": new_admin.role_name,
    }


def update_admin_user_controller(
    db: Session,
    admin_id: int,
    data: AdminUserUpdateSchema,
    current_admin: User,
    request: Optional[Request] = None,
) -> Dict[str, Any]:
    """Update administrator profile attributes or role."""
    admin = get_admin_user_by_id(db, admin_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Platform administrator with ID {admin_id} not found",
        )

    updated = update_admin_user_record(db, admin, data.model_dump(exclude_unset=True))

    log_audit_event(
        db,
        action="UPDATE_ADMIN_USER",
        module="ADMIN_MANAGEMENT",
        description=f"Super Admin {current_admin.email} updated admin user {updated.email}",
        user_id=current_admin.id,
        user_email=current_admin.email,
        user_type="super_admin",
        request=request,
    )

    return {
        "id": str(updated.id),
        "email": updated.email,
        "role": updated.role_name,
    }


def deactivate_admin_user_controller(
    db: Session,
    admin_id: int,
    current_admin: User,
    request: Optional[Request] = None,
) -> bool:
    """Toggle active state on an administrator account."""
    admin = get_admin_user_by_id(db, admin_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Platform administrator with ID {admin_id} not found",
        )

    is_active = toggle_admin_user_active_state(db, admin)
    action_label = "ACTIVATE_ADMIN" if is_active else "DEACTIVATE_ADMIN"

    log_audit_event(
        db,
        action=action_label,
        module="ADMIN_MANAGEMENT",
        description=f"Super Admin {current_admin.email} set active={is_active} on admin {admin.email}",
        user_id=current_admin.id,
        user_email=current_admin.email,
        user_type="super_admin",
        request=request,
    )

    return is_active
