# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/users/service.py
# Purpose : Domain & persistence logic for Platform User Management
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from shared.models import User, Role
from shared.utils import hash_password
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("admin_users_service")


@service_error_handler
def compute_user_stats(db: Session) -> Dict[str, Any]:
    """Calculate platform user statistics."""
    total = db.query(User).count()
    active = db.query(User).filter(User.is_active == True).count()
    inactive = total - active
    super_admins = db.query(User).filter(User.user_type == "super_admin").count()
    companies = db.query(User).filter(User.user_type == "company").count()
    jobseekers = db.query(User).filter(User.user_type == "jobseeker").count()

    return {
        "total": total,
        "active": active,
        "inactive": inactive,
        "super_admins": super_admins,
        "companies": companies,
        "jobseekers": jobseekers,
    }


def serialize_user(u: User) -> Dict[str, Any]:
    """Serialize User model."""
    return {
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
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


@service_error_handler
def list_platform_users(
    db: Session,
    search: Optional[str] = None,
    role: Optional[str] = None,
    status_filter: Optional[str] = None,
    user_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieve paginated platform user accounts with search and filters."""
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

    items = [serialize_user(u) for u in users]
    return items, total_items


@service_error_handler
def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Fetch user by id."""
    return db.query(User).filter(User.id == user_id).first()


@service_error_handler
def create_new_user(db: Session, data: Dict[str, Any]) -> User:
    """Create user record with assigned roles."""
    roles = []
    if data.get("role_ids"):
        roles = db.query(Role).filter(Role.id.in_(data["role_ids"])).all()

    new_user = User(
        email=data["email"].lower(),
        hashed_password=hash_password(data["password"]),
        full_name=data.get("full_name"),
        phone=data.get("phone"),
        user_type=data.get("user_type", "jobseeker"),
        is_active=data.get("is_active", True),
        is_verified=True,
        roles=roles,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    logger.info(f"Admin created user id={new_user.id} email={new_user.email}")
    return new_user


@service_error_handler
def update_user_record(db: Session, user: User, data: Dict[str, Any]) -> User:
    """Update user attributes."""
    if data.get("full_name") is not None:
        user.full_name = data["full_name"]
    if data.get("phone") is not None:
        user.phone = data["phone"]
    if data.get("avatar_url") is not None:
        user.avatar_url = data["avatar_url"]
    if data.get("is_active") is not None:
        user.is_active = data["is_active"]

    if data.get("role_ids") is not None:
        roles = db.query(Role).filter(Role.id.in_(data["role_ids"])).all()
        user.roles = roles

    db.commit()
    db.refresh(user)
    logger.info(f"Admin updated user id={user.id}")
    return user


@service_error_handler
def toggle_user_active_state(db: Session, user: User) -> bool:
    """Toggle is_active on user."""
    user.is_active = not user.is_active
    db.commit()
    logger.info(f"Toggled active state on user id={user.id} -> {user.is_active}")
    return user.is_active


@service_error_handler
def assign_roles(db: Session, user: User, role_ids: List[int]) -> None:
    """Assign roles to user."""
    roles = db.query(Role).filter(Role.id.in_(role_ids)).all()
    user.roles = roles
    db.commit()
    logger.info(f"Assigned {len(roles)} roles to user id={user.id}")
