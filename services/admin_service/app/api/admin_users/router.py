# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/admin_users/router.py
# Purpose : HTTP Routing endpoints for Platform Administrator Management
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import User
from shared.schemas import PaginatedResponse, APIResponse
from shared.utils import require_roles, success_response, paginated_response
from .schemas import AdminUserCreateSchema, AdminUserUpdateSchema
from .controller import (
    list_admin_roles_controller,
    list_admin_users_controller,
    get_admin_user_detail_controller,
    create_admin_user_controller,
    update_admin_user_controller,
    deactivate_admin_user_controller,
)

router = APIRouter(prefix="/admin-users", tags=["Platform Administrator Management"])


@router.get("/roles", response_model=APIResponse[list])
def list_admin_roles(
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    """List all platform admin roles and their permissions."""
    items = list_admin_roles_controller(db)
    return success_response(data=items)


@router.get("", response_model=PaginatedResponse[dict])
def list_admin_users(
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    """List platform administrator accounts from dedicated admin_users table."""
    items, total_items = list_admin_users_controller(
        db=db,
        search=search,
        role=role,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )
    return paginated_response(
        items=items,
        total_items=total_items,
        page=page,
        page_size=page_size,
        message="Platform administrators retrieved",
    )


@router.post("", response_model=APIResponse[dict])
def create_admin_user(
    data: AdminUserCreateSchema,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
):
    """Create a new dedicated platform administrator (Super Admin only)."""
    res = create_admin_user_controller(
        db=db,
        data=data,
        current_admin=current_admin,
        request=request,
    )
    return success_response(data=res, message="Platform administrator created successfully")


@router.get("/{admin_id}", response_model=APIResponse[dict])
def get_admin_user(
    admin_id: int,
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    """Get single administrator profile."""
    data = get_admin_user_detail_controller(db=db, admin_id=admin_id)
    return success_response(data=data)


@router.put("/{admin_id}", response_model=APIResponse[dict])
def update_admin_user(
    admin_id: int,
    data: AdminUserUpdateSchema,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
):
    """Update administrator details, role, or active status (Super Admin only)."""
    res = update_admin_user_controller(
        db=db,
        admin_id=admin_id,
        data=data,
        current_admin=current_admin,
        request=request,
    )
    return success_response(data=res, message="Platform administrator updated successfully")


@router.delete("/{admin_id}", response_model=APIResponse[None])
def deactivate_admin_user(
    admin_id: int,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
):
    """Deactivate or toggle platform administrator account (Super Admin only)."""
    is_active = deactivate_admin_user_controller(
        db=db,
        admin_id=admin_id,
        current_admin=current_admin,
        request=request,
    )
    status_str = "activated" if is_active else "deactivated"
    return success_response(message=f"Administrator account has been {status_str}")
