# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/roles/router.py
# Purpose : HTTP Routing endpoints for Role and Permission Management
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import User
from shared.schemas import APIResponse
from shared.utils import require_roles, success_response
from .schemas import RoleCreateSchema, RoleUpdateSchema
from .controller import (
    list_modules_and_permissions_controller,
    list_roles_controller,
    get_role_detail_controller,
    create_role_controller,
    update_role_controller,
    delete_role_controller,
)

router = APIRouter(prefix="/roles", tags=["Admin Role & Permission Management"])


@router.get("/modules", response_model=APIResponse[list])
def list_modules_and_permissions(
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    """List all system modules and their associated permissions."""
    data = list_modules_and_permissions_controller(db)
    return success_response(data=data)


@router.get("", response_model=APIResponse[list])
def list_roles(
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    """Retrieve all roles with assigned permissions and active user count."""
    data = list_roles_controller(db)
    return success_response(data=data)


@router.get("/{role_id}", response_model=APIResponse[dict])
def get_role_detail(
    role_id: int,
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    """Fetch details and permissions for a specific role."""
    data = get_role_detail_controller(db=db, role_id=role_id)
    return success_response(data=data)


@router.post("", response_model=APIResponse[dict])
def create_role(
    data: RoleCreateSchema,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
):
    """Create a new role with specific permissions (Super Admin only)."""
    res = create_role_controller(
        db=db,
        data=data,
        current_admin=current_admin,
        request=request,
    )
    return success_response(data=res, message="Role created successfully")


@router.put("/{role_id}", response_model=APIResponse[dict])
def update_role(
    role_id: int,
    data: RoleUpdateSchema,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
):
    """Update role details and permissions (Super Admin only)."""
    res = update_role_controller(
        db=db,
        role_id=role_id,
        data=data,
        current_admin=current_admin,
        request=request,
    )
    return success_response(data=res, message="Role updated successfully")


@router.delete("/{role_id}", response_model=APIResponse[None])
def delete_role(
    role_id: int,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
):
    """Delete a role (Super Admin only, system roles cannot be deleted)."""
    delete_role_controller(
        db=db,
        role_id=role_id,
        current_admin=current_admin,
        request=request,
    )
    return success_response(message="Role deleted successfully")
