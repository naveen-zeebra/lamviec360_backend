# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/admin_users/service.py
# Purpose : Domain & database logic for Platform Administrator Management
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from shared.models import AdminUser, AdminRole
from shared.utils import hash_password
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("admin_management_service")


def serialize_admin_role_item(r: AdminRole) -> Dict[str, Any]:
    """Serialize AdminRole model to dict with nested permissions."""
    perms = {}
    for p in (r.permissions or []):
        perms[p.module_key] = {
            "can_view": p.can_view,
            "can_create": p.can_create,
            "can_edit": p.can_edit,
            "can_delete": p.can_delete,
        }
    return {
        "id": str(r.id),
        "name": r.name,
        "code": r.code,
        "description": r.description,
        "is_system": r.is_system,
        "user_count": len(r.admins) if r.admins else 0,
        "permissions": perms,
    }


def serialize_admin_user_item(a: AdminUser) -> Dict[str, Any]:
    """Serialize AdminUser model to dict."""
    return {
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
    }


@service_error_handler
def get_all_admin_roles(db: Session) -> List[Dict[str, Any]]:
    """Fetch all admin roles from admin_roles table."""
    roles = db.query(AdminRole).all()
    return [serialize_admin_role_item(r) for r in roles]


@service_error_handler
def query_admin_users(
    db: Session,
    search: Optional[str] = None,
    role: Optional[str] = None,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> Tuple[List[Dict[str, Any]], int]:
    """Query paginated AdminUser records with filters."""
    query = db.query(AdminUser).filter(AdminUser.is_deleted == False)

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                AdminUser.email.ilike(term),
                AdminUser.first_name.ilike(term),
                AdminUser.last_name.ilike(term),
            )
        )

    if role and role != "All":
        query = query.filter(AdminUser.role_name == role)

    if status_filter and status_filter != "All":
        is_act = True if status_filter.lower() == "active" else False
        query = query.filter(AdminUser.is_active == is_act)

    total_items = query.count()
    offset = (page - 1) * page_size
    admins = query.order_by(desc(AdminUser.created_at)).offset(offset).limit(page_size).all()

    items = [serialize_admin_user_item(a) for a in admins]
    return items, total_items


@service_error_handler
def get_admin_user_by_id(db: Session, admin_id: int) -> Optional[AdminUser]:
    """Fetch non-deleted AdminUser by ID."""
    return db.query(AdminUser).filter(
        AdminUser.id == admin_id,
        AdminUser.is_deleted == False,
    ).first()


@service_error_handler
def get_admin_user_by_email(db: Session, email: str) -> Optional[AdminUser]:
    """Fetch AdminUser by email address."""
    return db.query(AdminUser).filter(AdminUser.email == email.lower()).first()


@service_error_handler
def create_admin_user_record(db: Session, data: Dict[str, Any]) -> AdminUser:
    """Create a new AdminUser record."""
    role_obj = db.query(AdminRole).filter(
        or_(AdminRole.name == data.get("role"), AdminRole.code == data.get("role"))
    ).first()
    role_name = role_obj.name if role_obj else data.get("role", "Operations Admin")

    new_admin = AdminUser(
        email=data["email"].lower(),
        password_hash=hash_password(data["password"]),
        first_name=data["first_name"],
        last_name=data["last_name"],
        phone=data.get("phone"),
        role_id=role_obj.id if role_obj else None,
        role_name=role_name,
        is_active=data.get("is_active", True),
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    logger.info(f"Created AdminUser id={new_admin.id} email={new_admin.email}")
    return new_admin


@service_error_handler
def update_admin_user_record(db: Session, admin: AdminUser, data: Dict[str, Any]) -> AdminUser:
    """Update fields on an AdminUser record."""
    if data.get("first_name") is not None:
        admin.first_name = data["first_name"]
    if data.get("last_name") is not None:
        admin.last_name = data["last_name"]
    if data.get("phone") is not None:
        admin.phone = data["phone"]
    if data.get("is_active") is not None:
        admin.is_active = data["is_active"]
    if data.get("role") is not None:
        role_obj = db.query(AdminRole).filter(
            or_(AdminRole.name == data["role"], AdminRole.code == data["role"])
        ).first()
        admin.role_id = role_obj.id if role_obj else admin.role_id
        admin.role_name = role_obj.name if role_obj else data["role"]

    db.commit()
    db.refresh(admin)
    logger.info(f"Updated AdminUser id={admin.id}")
    return admin


@service_error_handler
def toggle_admin_user_active_state(db: Session, admin: AdminUser) -> bool:
    """Toggle is_active flag on AdminUser."""
    admin.is_active = not admin.is_active
    db.commit()
    db.refresh(admin)
    logger.info(f"Toggled active state on AdminUser id={admin.id} -> {admin.is_active}")
    return admin.is_active
