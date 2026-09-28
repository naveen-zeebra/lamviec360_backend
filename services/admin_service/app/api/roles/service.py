# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/roles/service.py
# Purpose : Domain & database logic for Role and Permission management
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from shared.models import Role, RolePermission
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("admin_roles_service")


@service_error_handler
def get_grouped_modules_and_permissions(db: Session) -> List[Dict[str, Any]]:
    """Retrieve all role permissions grouped by module."""
    perms = db.query(RolePermission).all()
    module_dict: Dict[str, List[Dict[str, Any]]] = {}
    for p in perms:
        if p.module not in module_dict:
            module_dict[p.module] = []
        module_dict[p.module].append({
            "id": p.id,
            "action": p.action,
            "description": p.description,
        })

    return [{"module": mod, "permissions": items} for mod, items in module_dict.items()]


def serialize_role(r: Role) -> Dict[str, Any]:
    """Serialize a Role ORM object with its attached permissions."""
    return {
        "id": r.id,
        "name": r.name,
        "code": r.code,
        "description": r.description,
        "is_system": r.is_system,
        "is_active": r.is_active,
        "user_count": len(r.users) if r.users else 0,
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
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


@service_error_handler
def get_all_roles_with_permissions(db: Session) -> List[Dict[str, Any]]:
    """Fetch all roles with associated permissions and member counts."""
    roles = db.query(Role).all()
    return [serialize_role(r) for r in roles]


@service_error_handler
def get_role_by_id(db: Session, role_id: int) -> Optional[Role]:
    """Fetch role by its primary key ID."""
    return db.query(Role).filter(Role.id == role_id).first()


@service_error_handler
def get_role_by_code(db: Session, code: str) -> Optional[Role]:
    """Fetch role by unique code identifier."""
    return db.query(Role).filter(Role.code == code.lower()).first()


@service_error_handler
def create_role_record(db: Session, data: Dict[str, Any]) -> Role:
    """Create a new Role record with attached permissions."""
    perms = []
    if data.get("permission_ids"):
        perms = db.query(RolePermission).filter(RolePermission.id.in_(data["permission_ids"])).all()

    role = Role(
        name=data["name"],
        code=data["code"].lower(),
        description=data.get("description"),
        is_active=data.get("is_active", True),
        is_system=False,
        permissions=perms,
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    logger.info(f"Created role '{role.name}' ({role.code}) id={role.id}")
    return role


@service_error_handler
def update_role_record(db: Session, role: Role, data: Dict[str, Any]) -> Role:
    """Update role details and permissions."""
    if data.get("name") is not None:
        role.name = data["name"]
    if data.get("description") is not None:
        role.description = data["description"]
    if data.get("is_active") is not None:
        role.is_active = data["is_active"]

    if data.get("permission_ids") is not None:
        perms = db.query(RolePermission).filter(RolePermission.id.in_(data["permission_ids"])).all()
        role.permissions = perms

    db.commit()
    db.refresh(role)
    logger.info(f"Updated role id={role.id} '{role.name}'")
    return role


@service_error_handler
def delete_role_record(db: Session, role: Role) -> None:
    """Delete a role record from database."""
    db.delete(role)
    db.commit()
    logger.info(f"Deleted role id={role.id}")
