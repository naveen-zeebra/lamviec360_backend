# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/users/controller.py
# Purpose : Orchestration layer for Platform User Management
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session

from shared.models import User
from shared.utils import log_audit_event
from shared.utils.logger import get_logger
from .schemas import UserCreateSchema, UserUpdateSchema
from .service import (
    compute_user_stats,
    list_platform_users,
    get_user_by_id,
    create_new_user,
    update_user_record,
    toggle_user_active_state,
    assign_roles,
)

logger = get_logger("admin_users_controller")


def get_user_stats_controller(db: Session) -> Dict[str, Any]:
    """Return user distribution statistics across the platform."""
    return compute_user_stats(db)


def list_users_controller(
    db: Session,
    search: Optional[str] = None,
    role: Optional[str] = None,
    status_filter: Optional[str] = None,
    user_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieve filtered and paginated list of platform users."""
    return list_platform_users(
        db=db,
        search=search,
        role=role,
        status_filter=status_filter,
        user_type=user_type,
        page=page,
        page_size=page_size,
    )


def get_user_detail_controller(db: Session, user_id: Any) -> Dict[str, Any]:
    """Fetch complete detail for a single platform user."""
    u = get_user_by_id(db, user_id)
    if not u:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )
    roles = []
    for r in (getattr(u, "roles", []) or []):
        roles.append({
            "id": getattr(r, "id", None),
            "name": getattr(r, "name", str(r)),
            "code": getattr(r, "code", str(r)),
        })
    company_name = None
    if hasattr(u, "company") and u.company:
        company_name = getattr(u.company, "company_name", None) or getattr(u.company, "legal_name", None)

    return {
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "phone": u.phone,
        "avatar_url": u.avatar_url,
        "user_type": getattr(u, "user_type", "jobseeker"),
        "company": company_name,
        "company_id": getattr(u, "company_id", None),
        "role": getattr(u, "role", "User"),
        "is_active": u.is_active,
        "is_verified": u.is_verified,
        "is_superuser": getattr(u, "is_superuser", False),
        "roles": roles,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "updated_at": u.updated_at.isoformat() if hasattr(u, "updated_at") and u.updated_at else None,
    }


def create_user_controller(
    db: Session,
    data: UserCreateSchema,
    current_admin: User,
    request: Optional[Request] = None,
) -> Dict[str, Any]:
    """Create a new platform user account."""
    existing = db.query(User).filter(User.email == data.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )

    new_user = create_new_user(db, data.model_dump())

    log_audit_event(
        db,
        action="CREATE_USER",
        module="ADMIN_USERS",
        description=f"Admin {current_admin.email} created user {new_user.email}",
        user_id=current_admin.id,
        user_email=current_admin.email,
        user_type=current_admin.user_type,
        request=request,
    )

    return {"id": new_user.id, "email": new_user.email}


def update_user_controller(
    db: Session,
    user_id: Any,
    data: UserUpdateSchema,
    current_admin: User,
    request: Optional[Request] = None,
) -> Dict[str, Any]:
    """Update profile and permissions for a platform user."""
    u = get_user_by_id(db, user_id)
    if not u:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    updated = update_user_record(db, u, data.model_dump(exclude_unset=True))

    log_audit_event(
        db,
        action="UPDATE_USER",
        module="ADMIN_USERS",
        description=f"Admin {current_admin.email} updated user {updated.email}",
        user_id=current_admin.id,
        user_email=current_admin.email,
        user_type=current_admin.user_type,
        request=request,
    )

    return {"id": updated.id, "email": updated.email}


def toggle_user_active_controller(
    db: Session,
    user_id: Any,
    current_admin: User,
    request: Optional[Request] = None,
) -> bool:
    """Toggle user active status or deactivate account."""
    u = get_user_by_id(db, user_id)
    if not u:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    if hasattr(u, "id") and u.id == current_admin.id and not str(user_id).startswith("cu_"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate or delete your own account",
        )

    new_state = toggle_user_active_state(db, u)
    action_label = "ACTIVATE_USER" if new_state else "DEACTIVATE_USER"

    log_audit_event(
        db,
        action=action_label,
        module="ADMIN_USERS",
        description=f"Admin {current_admin.email} set status={new_state} on user {u.email}",
        user_id=current_admin.id,
        user_email=current_admin.email,
        user_type=current_admin.user_type,
        request=request,
    )

    return new_state


def assign_roles_controller(
    db: Session,
    user_id: int,
    role_ids: List[int],
    current_admin: User,
    request: Optional[Request] = None,
) -> None:
    """Assign RBAC roles to a user account."""
    u = get_user_by_id(db, user_id)
    if not u:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    assign_roles(db, u, role_ids)

    log_audit_event(
        db,
        action="ASSIGN_ROLES",
        module="ADMIN_USERS",
        description=f"Admin {current_admin.email} assigned roles to {u.email}",
        user_id=current_admin.id,
        user_email=current_admin.email,
        user_type=current_admin.user_type,
        request=request,
    )
