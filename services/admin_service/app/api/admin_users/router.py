from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from pydantic import BaseModel, EmailStr, Field

from shared.database.session import get_db
from shared.models import AdminUser, AdminRole, AdminRolePermission, User
from shared.schemas import PaginatedResponse, APIResponse
from shared.utils import (
    get_current_user,
    require_roles,
    hash_password,
    success_response,
    paginated_response,
    log_audit_event,
)

router = APIRouter(prefix="/admin-users", tags=["Platform Administrator Management"])

class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    first_name: str
    last_name: str
    phone: Optional[str] = None
    role: str = "Operations Admin"  # "Super Admin", "Operations Admin", etc.
    is_active: bool = True

class AdminUserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class PermissionUpdateItem(BaseModel):
    module_key: str
    can_view: bool
    can_create: bool
    can_edit: bool
    can_delete: bool

class RoleUpdateRequest(BaseModel):
    permissions: List[PermissionUpdateItem]


@router.get("/roles", response_model=APIResponse[list])
def list_admin_roles(
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    """List all platform admin roles and their permissions."""
    roles = db.query(AdminRole).all()
    items = []
    for r in roles:
        perms = {}
        for p in r.permissions:
            perms[p.module_key] = {
                "can_view": p.can_view,
                "can_create": p.can_create,
                "can_edit": p.can_edit,
                "can_delete": p.can_delete,
            }
        items.append({
            "id": str(r.id),
            "name": r.name,
            "code": r.code,
            "description": r.description,
            "is_system": r.is_system,
            "user_count": len(r.admins),
            "permissions": perms,
        })
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
    query = db.query(AdminUser).filter(AdminUser.is_deleted == False)

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(or_(AdminUser.email.ilike(term), AdminUser.first_name.ilike(term), AdminUser.last_name.ilike(term)))

    if role and role != "All":
        query = query.filter(AdminUser.role_name == role)

    if status_filter and status_filter != "All":
        is_act = True if status_filter.lower() == "active" else False
        query = query.filter(AdminUser.is_active == is_act)

    total_items = query.count()
    offset = (page - 1) * page_size
    admins = query.order_by(desc(AdminUser.created_at)).offset(offset).limit(page_size).all()

    items = []
    for a in admins:
        items.append({
            "id": str(a.id),
            "email": a.email,
            "first_name": a.first_name,
            "last_name": a.last_name,
            "name": a.full_name,
            "phone": a.phone,
            "role": a.role_name,
            "is_active": a.is_active,
            "status": "Active" if a.is_active else "Inactive",
            "permissions": a.permissions_dict,
            "avatar": a.avatar_url,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "last_login": a.last_login.isoformat() if a.last_login else None,
        })

    return paginated_response(
        items=items,
        total_items=total_items,
        page=page,
        page_size=page_size,
        message="Platform administrators retrieved",
    )


@router.post("", response_model=APIResponse[dict])
def create_admin_user(
    data: AdminUserCreate,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
):
    """Create a new dedicated platform administrator."""
    existing = db.query(AdminUser).filter(AdminUser.email == data.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="An administrator account with this email already exists")

    # Match role
    role_obj = db.query(AdminRole).filter(or_(AdminRole.name == data.role, AdminRole.code == data.role)).first()
    role_name = role_obj.name if role_obj else data.role

    new_admin = AdminUser(
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        role_id=role_obj.id if role_obj else None,
        role_name=role_name,
        is_active=data.is_active,
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

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

    return success_response(
        data={
            "id": str(new_admin.id),
            "email": new_admin.email,
            "name": new_admin.full_name,
            "role": new_admin.role_name,
        },
        message="Platform administrator created successfully",
    )


@router.get("/{admin_id}", response_model=APIResponse[dict])
def get_admin_user(
    admin_id: int,
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    """Get single administrator profile."""
    a = db.query(AdminUser).filter(AdminUser.id == admin_id, AdminUser.is_deleted == False).first()
    if not a:
        raise HTTPException(status_code=404, detail="Platform administrator not found")

    return success_response(
        data={
            "id": str(a.id),
            "email": a.email,
            "first_name": a.first_name,
            "last_name": a.last_name,
            "name": a.full_name,
            "phone": a.phone,
            "role": a.role_name,
            "is_active": a.is_active,
            "permissions": a.permissions_dict,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "last_login": a.last_login.isoformat() if a.last_login else None,
        }
    )


@router.put("/{admin_id}", response_model=APIResponse[dict])
def update_admin_user(
    admin_id: int,
    data: AdminUserUpdate,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
):
    """Update administrator details, role, or active status."""
    a = db.query(AdminUser).filter(AdminUser.id == admin_id, AdminUser.is_deleted == False).first()
    if not a:
        raise HTTPException(status_code=404, detail="Platform administrator not found")

    if data.first_name is not None:
        a.first_name = data.first_name
    if data.last_name is not None:
        a.last_name = data.last_name
    if data.phone is not None:
        a.phone = data.phone
    if data.is_active is not None:
        a.is_active = data.is_active
    if data.role is not None:
        role_obj = db.query(AdminRole).filter(or_(AdminRole.name == data.role, AdminRole.code == data.role)).first()
        a.role_id = role_obj.id if role_obj else a.role_id
        a.role_name = role_obj.name if role_obj else data.role

    db.commit()
    db.refresh(a)

    log_audit_event(
        db,
        action="UPDATE_ADMIN_USER",
        module="ADMIN_MANAGEMENT",
        description=f"Super Admin {current_admin.email} updated admin user {a.email}",
        user_id=current_admin.id,
        user_email=current_admin.email,
        user_type="super_admin",
        request=request,
    )

    return success_response(
        data={"id": str(a.id), "email": a.email, "role": a.role_name},
        message="Platform administrator updated successfully",
    )


@router.delete("/{admin_id}", response_model=APIResponse[None])
def deactivate_admin_user(
    admin_id: int,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
):
    """Deactivate or toggle platform administrator account."""
    a = db.query(AdminUser).filter(AdminUser.id == admin_id, AdminUser.is_deleted == False).first()
    if not a:
        raise HTTPException(status_code=404, detail="Platform administrator not found")

    a.is_active = not a.is_active
    db.commit()

    action_label = "ACTIVATE_ADMIN" if a.is_active else "DEACTIVATE_ADMIN"
    log_audit_event(
        db,
        action=action_label,
        module="ADMIN_MANAGEMENT",
        description=f"Super Admin {current_admin.email} set active={a.is_active} on admin {a.email}",
        user_id=current_admin.id,
        user_email=current_admin.email,
        user_type="super_admin",
        request=request,
    )

    status_str = "activated" if a.is_active else "deactivated"
    return success_response(message=f"Administrator account has been {status_str}")
