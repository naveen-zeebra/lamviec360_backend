# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/users/router.py
# Purpose : Thin HTTP routing endpoints for Platform User Management
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import User
from shared.schemas import PaginatedResponse, APIResponse
from shared.utils import (
    require_roles,
    success_response,
    paginated_response,
)
from .schemas import UserCreateSchema, UserUpdateSchema, AssignRolesRequest
from .controller import (
    get_user_stats_controller,
    list_users_controller,
    get_user_detail_controller,
    create_user_controller,
    update_user_controller,
    toggle_user_active_controller,
    assign_roles_controller,
)

router = APIRouter(prefix="/users", tags=["Admin User Management"])


@router.get("/stats", response_model=APIResponse[dict])
def get_user_stats(
    user: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    """Get aggregated statistics on registered users."""
    stats = get_user_stats_controller(db)
    return success_response(data=stats)


@router.get("", response_model=PaginatedResponse[dict])
def list_users(
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    user_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    """Retrieve paginated list of users with multi-attribute filtering."""
    items, total_items = list_users_controller(
        db=db,
        search=search,
        role=role,
        status_filter=status_filter,
        user_type=user_type,
        page=page,
        page_size=page_size,
    )
    return paginated_response(
        items=items,
        total_items=total_items,
        page=page,
        page_size=page_size,
        message="Users fetched successfully",
    )


@router.get("/{user_id}", response_model=APIResponse[dict])
def get_user_detail(
    user_id: str,
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    """Fetch complete detail of a user by ID."""
    data = get_user_detail_controller(db=db, user_id=user_id)
    return success_response(data=data)


@router.post("", response_model=APIResponse[dict])
def create_user(
    data: UserCreateSchema,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    """Register a new platform user."""
    res = create_user_controller(
        db=db,
        data=data,
        current_admin=current_admin,
        request=request,
    )
    return success_response(data=res, message="User created successfully")


@router.put("/{user_id}", response_model=APIResponse[dict])
def update_user(
    user_id: str,
    data: UserUpdateSchema,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    """Update profile and permissions for a user."""
    res = update_user_controller(
        db=db,
        user_id=user_id,
        data=data,
        current_admin=current_admin,
        request=request,
    )
    return success_response(data=res, message="User updated successfully")


@router.delete("/{user_id}", response_model=APIResponse[None])
def toggle_or_delete_user(
    user_id: str,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
):
    """Toggle user active status (deactivate / activate)."""
    new_state = toggle_user_active_controller(
        db=db,
        user_id=user_id,
        current_admin=current_admin,
        request=request,
    )
    status_str = "activated" if new_state else "deactivated"
    return success_response(message=f"User has been {status_str} successfully")


@router.put("/{user_id}/roles", response_model=APIResponse[dict])
def assign_user_roles(
    user_id: str,
    req: AssignRolesRequest,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
):
    """Assign RBAC roles to a user."""
    assign_roles_controller(
        db=db,
        user_id=user_id,
        role_ids=req.role_ids,
        current_admin=current_admin,
        request=request,
    )
    return success_response(message="Roles assigned successfully")
