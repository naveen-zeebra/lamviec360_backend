# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/roles/controller.py
# Purpose : Orchestration layer for Role & Permission Management
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session

from shared.models import User
from shared.utils import log_audit_event
from shared.utils.logger import get_logger
from .schemas import RoleCreateSchema, RoleUpdateSchema
from .service import (
    get_grouped_modules_and_permissions,
    get_all_roles_with_permissions,
    get_role_by_id,
    get_role_by_code,
    create_role_record,
    update_role_record,
    delete_role_record,
    serialize_role,
)

logger = get_logger("admin_roles_controller")


def list_modules_and_permissions_controller(db: Session) -> List[Dict[str, Any]]:
    """Return all system permissions grouped by module."""
    return get_grouped_modules_and_permissions(db)


def list_roles_controller(db: Session) -> List[Dict[str, Any]]:
    """Return all roles with permissions and member counts."""
    return get_all_roles_with_permissions(db)


def get_role_detail_controller(db: Session, role_id: int) -> Dict[str, Any]:
    """Return detailed information for a single role."""
    role = get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found",
        )
    return serialize_role(role)


def create_role_controller(
    db: Session,
    data: RoleCreateSchema,
    current_admin: User,
    request: Optional[Request] = None,
) -> Dict[str, Any]:
    """Create a new custom role."""
    existing = get_role_by_code(db, data.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A role with this code already exists",
        )

    role = create_role_record(db, data.model_dump())

    log_audit_event(
        db,
        action="CREATE_ROLE",
        module="ADMIN_ROLES",
        description=f"Admin {current_admin.email} created role '{role.name}' ({role.code})",
        user_id=current_admin.id,
        user_email=current_admin.email,
        user_type=current_admin.user_type,
        request=request,
    )

    return {"id": role.id, "code": role.code}


def update_role_controller(
    db: Session,
    role_id: int,
    data: RoleUpdateSchema,
    current_admin: User,
    request: Optional[Request] = None,
) -> Dict[str, Any]:
    """Update role details and its attached permissions."""
    role = get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found",
        )

    updated = update_role_record(db, role, data.model_dump(exclude_unset=True))

    log_audit_event(
        db,
        action="UPDATE_ROLE",
        module="ADMIN_ROLES",
        description=f"Admin {current_admin.email} updated role '{updated.name}'",
        user_id=current_admin.id,
        user_email=current_admin.email,
        user_type=current_admin.user_type,
        request=request,
    )

    return {"id": updated.id, "code": updated.code}


def delete_role_controller(
    db: Session,
    role_id: int,
    current_admin: User,
    request: Optional[Request] = None,
) -> None:
    """Delete a custom non-system role."""
    role = get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found",
        )

    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System protected roles cannot be deleted",
        )

    delete_role_record(db, role)

    log_audit_event(
        db,
        action="DELETE_ROLE",
        module="ADMIN_ROLES",
        description=f"Admin {current_admin.email} deleted role '{role.name}'",
        user_id=current_admin.id,
        user_email=current_admin.email,
        user_type=current_admin.user_type,
        request=request,
    )
