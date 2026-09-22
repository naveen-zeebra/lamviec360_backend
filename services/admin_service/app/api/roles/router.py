from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import Role, RolePermission, User
from shared.schemas import RoleCreate, RoleUpdate, APIResponse
from shared.utils import get_current_user, require_roles, success_response, log_audit_event

router = APIRouter(prefix="/roles", tags=["Admin Role & Permission Management"])

@router.get("/modules", response_model=APIResponse[list])
def list_modules_and_permissions(
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    perms = db.query(RolePermission).all()
    # Group by module
    module_dict = {}
    for p in perms:
        if p.module not in module_dict:
            module_dict[p.module] = []
        module_dict[p.module].append({
            "id": p.id,
            "action": p.action,
            "description": p.description,
        })

    result = [{"module": mod, "permissions": items} for mod, items in module_dict.items()]
    return success_response(data=result)


@router.get("", response_model=APIResponse[list])
def list_roles(
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    roles = db.query(Role).all()
    results = []
    for r in roles:
        results.append({
            "id": r.id,
            "name": r.name,
            "code": r.code,
            "description": r.description,
            "is_system": r.is_system,
            "is_active": r.is_active,
            "user_count": len(r.users),
            "permissions": [
                {
                    "id": p.id,
                    "module_key": p.module_key,
                    "module": p.module,
                    "can_view": p.can_view,
                    "can_create": p.can_create,
                    "can_edit": p.can_edit,
                    "can_delete": p.can_delete,
                    "action": p.action,
                    "description": p.description,
                }
                for p in r.permissions
            ],
            "created_at": r.created_at,
        })
    return success_response(data=results)


@router.get("/{role_id}", response_model=APIResponse[dict])
def get_role_detail(
    role_id: int,
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    return success_response(
        data={
            "id": role.id,
            "name": role.name,
            "code": role.code,
            "description": role.description,
            "is_system": role.is_system,
            "is_active": role.is_active,
            "permissions": [
                {
                    "id": p.id,
                    "module_key": p.module_key,
                    "module": p.module,
                    "can_view": p.can_view,
                    "can_create": p.can_create,
                    "can_edit": p.can_edit,
                    "can_delete": p.can_delete,
                    "action": p.action,
                    "description": p.description,
                }
                for p in role.permissions
            ],
        }
    )


@router.post("", response_model=APIResponse[dict])
def create_role(
    data: RoleCreate,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
):
    existing = db.query(Role).filter(Role.code == data.code.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="A role with this code already exists")

    perms = []
    if data.permission_ids:
        perms = db.query(RolePermission).filter(RolePermission.id.in_(data.permission_ids)).all()

    role = Role(
        name=data.name,
        code=data.code.lower(),
        description=data.description,
        is_active=data.is_active,
        is_system=False,
        permissions=perms,
    )
    db.add(role)
    db.commit()
    db.refresh(role)

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

    return success_response(data={"id": role.id, "code": role.code}, message="Role created successfully")


@router.put("/{role_id}", response_model=APIResponse[dict])
def update_role(
    role_id: int,
    data: RoleUpdate,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if data.name:
        role.name = data.name
    if data.description is not None:
        role.description = data.description
    if data.is_active is not None:
        role.is_active = data.is_active

    if data.permission_ids is not None:
        perms = db.query(RolePermission).filter(RolePermission.id.in_(data.permission_ids)).all()
        role.permissions = perms

    db.commit()
    db.refresh(role)

    log_audit_event(
        db,
        action="UPDATE_ROLE",
        module="ADMIN_ROLES",
        description=f"Admin {current_admin.email} updated role '{role.name}'",
        user_id=current_admin.id,
        user_email=current_admin.email,
        user_type=current_admin.user_type,
        request=request,
    )

    return success_response(data={"id": role.id, "code": role.code}, message="Role updated successfully")


@router.delete("/{role_id}", response_model=APIResponse[None])
def delete_role(
    role_id: int,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if role.is_system:
        raise HTTPException(status_code=400, detail="System protected roles cannot be deleted")

    db.delete(role)
    db.commit()

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

    return success_response(message="Role deleted successfully")
