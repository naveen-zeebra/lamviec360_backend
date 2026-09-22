from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from pydantic import BaseModel

from shared.database.session import get_db
from shared.models import User, Role
from shared.schemas import UserCreate, UserUpdate, PaginatedResponse, APIResponse
from shared.utils import (
    get_current_user,
    require_roles,
    hash_password,
    success_response,
    paginated_response,
    log_audit_event,
)

router = APIRouter(prefix="/users", tags=["Admin User Management"])

class AssignRolesRequest(BaseModel):
    role_ids: List[int]

@router.get("/stats", response_model=APIResponse[dict])
def get_user_stats(
    user: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    total = db.query(User).count()
    active = db.query(User).filter(User.is_active == True).count()
    inactive = total - active
    super_admins = db.query(User).filter(User.user_type == "super_admin").count()
    companies = db.query(User).filter(User.user_type == "company").count()
    jobseekers = db.query(User).filter(User.user_type == "jobseeker").count()

    return success_response(
        data={
            "total": total,
            "active": active,
            "inactive": inactive,
            "super_admins": super_admins,
            "companies": companies,
            "jobseekers": jobseekers,
        }
    )

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
    query = db.query(User)

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(or_(User.email.ilike(term), User.full_name.ilike(term)))

    if user_type:
        query = query.filter(User.user_type == user_type)

    if status_filter:
        is_active = True if status_filter.lower() == "active" else False
        query = query.filter(User.is_active == is_active)

    if role:
        query = query.join(User.roles).filter(Role.code == role)

    total_items = query.count()
    offset = (page - 1) * page_size
    users = query.order_by(desc(User.created_at)).offset(offset).limit(page_size).all()

    items = []
    for u in users:
        items.append({
            "id": u.id,
            "email": u.email,
            "name": u.full_name,
            "full_name": u.full_name,
            "phone": u.phone,
            "avatar_url": u.avatar_url,
            "user_type": u.user_type,
            "status": "active" if u.is_active else "inactive",
            "is_active": u.is_active,
            "is_verified": u.is_verified,
            "is_superuser": u.is_superuser,
            "roles": [r.code for r in u.roles],
            "role_names": [r.name for r in u.roles],
            "role": u.roles[0].name if u.roles else "User",
            "created_at": u.created_at,
        })

    return paginated_response(
        items=items,
        total_items=total_items,
        page=page,
        page_size=page_size,
        message="Users fetched successfully",
    )


@router.get("/{user_id}", response_model=APIResponse[dict])
def get_user_detail(
    user_id: int,
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    return success_response(
        data={
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "phone": u.phone,
            "avatar_url": u.avatar_url,
            "user_type": u.user_type,
            "is_active": u.is_active,
            "is_verified": u.is_verified,
            "is_superuser": u.is_superuser,
            "roles": [{"id": r.id, "name": r.name, "code": r.code} for r in u.roles],
            "created_at": u.created_at,
            "updated_at": u.updated_at,
        }
    )


@router.post("", response_model=APIResponse[dict])
def create_user(
    data: UserCreate,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == data.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="A user with this email already exists")

    roles = []
    if data.role_ids:
        roles = db.query(Role).filter(Role.id.in_(data.role_ids)).all()

    new_user = User(
        email=data.email.lower(),
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        user_type=data.user_type,
        is_active=data.is_active,
        is_verified=True,
        roles=roles,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

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

    return success_response(data={"id": new_user.id, "email": new_user.email}, message="User created successfully")


@router.put("/{user_id}", response_model=APIResponse[dict])
def update_user(
    user_id: int,
    data: UserUpdate,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    if data.full_name is not None:
        u.full_name = data.full_name
    if data.phone is not None:
        u.phone = data.phone
    if data.avatar_url is not None:
        u.avatar_url = data.avatar_url
    if data.is_active is not None:
        u.is_active = data.is_active

    if data.role_ids is not None:
        roles = db.query(Role).filter(Role.id.in_(data.role_ids)).all()
        u.roles = roles

    db.commit()
    db.refresh(u)

    log_audit_event(
        db,
        action="UPDATE_USER",
        module="ADMIN_USERS",
        description=f"Admin {current_admin.email} updated user {u.email}",
        user_id=current_admin.id,
        user_email=current_admin.email,
        user_type=current_admin.user_type,
        request=request,
    )

    return success_response(data={"id": u.id, "email": u.email}, message="User updated successfully")


@router.delete("/{user_id}", response_model=APIResponse[None])
def toggle_or_delete_user(
    user_id: int,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    if u.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate or delete your own account")

    # Soft deactivate rather than hard delete
    u.is_active = not u.is_active
    db.commit()

    action_label = "DEACTIVATE_USER" if not u.is_active else "ACTIVATE_USER"
    log_audit_event(
        db,
        action=action_label,
        module="ADMIN_USERS",
        description=f"Admin {current_admin.email} set status={u.is_active} on user {u.email}",
        user_id=current_admin.id,
        user_email=current_admin.email,
        user_type=current_admin.user_type,
        request=request,
    )

    status_str = "activated" if u.is_active else "deactivated"
    return success_response(message=f"User has been {status_str} successfully")


@router.put("/{user_id}/roles", response_model=APIResponse[dict])
def assign_user_roles(
    user_id: int,
    req: AssignRolesRequest,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    roles = db.query(Role).filter(Role.id.in_(req.role_ids)).all()
    u.roles = roles
    db.commit()

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

    return success_response(message="Roles assigned successfully")
