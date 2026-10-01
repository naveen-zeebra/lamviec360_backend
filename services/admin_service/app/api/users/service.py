# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/users/service.py
# Purpose : Domain & persistence logic for Platform User Management
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from shared.models import User, Role, CompanyUser, CompanyProfile, AdminUser
from shared.utils import hash_password
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("admin_users_service")


@service_error_handler
def compute_user_stats(db: Session) -> Dict[str, Any]:
    """Calculate platform user statistics across all user systems."""
    total_jobseekers = db.query(User).filter(User.role_type == "jobseeker").count()
    active_jobseekers = db.query(User).filter(User.role_type == "jobseeker", User.is_active == True).count()

    total_company_users = db.query(CompanyUser).count()
    active_company_users = db.query(CompanyUser).filter(CompanyUser.is_active == True).count()

    total_companies = db.query(CompanyProfile).count()
    total_super_admins = db.query(AdminUser).count()

    return {
        "total": total_jobseekers + total_company_users,
        "active": active_jobseekers + active_company_users,
        "inactive": (total_jobseekers - active_jobseekers) + (total_company_users - active_company_users),
        "jobseekers": total_jobseekers,
        "active_jobseekers": active_jobseekers,
        "company_users": total_company_users,
        "active_company_users": active_company_users,
        "companies": total_companies,
        "super_admins": total_super_admins,
    }


def serialize_user(u: User) -> Dict[str, Any]:
    """Serialize User model (Candidate / Job Seeker)."""
    headline = None
    city = None
    skills = None
    resume_url = None
    applications_count = 0
    if hasattr(u, "jobseeker_profile") and u.jobseeker_profile:
        headline = u.jobseeker_profile.headline
        city = u.jobseeker_profile.city
        skills = u.jobseeker_profile.skills
        resume_url = u.jobseeker_profile.resume_url
        applications_count = len(u.jobseeker_profile.applications) if u.jobseeker_profile.applications else 0

    return {
        "id": str(u.id),
        "numeric_id": u.id,
        "email": u.email,
        "name": u.full_name,
        "full_name": u.full_name,
        "phone": u.phone,
        "avatar_url": u.avatar_url,
        "user_type": u.role_type or "jobseeker",
        "role": "Job Seeker" if (u.role_type == "jobseeker" or not u.roles) else u.roles[0].name,
        "roles": [r.code for r in u.roles] if u.roles else ["jobseeker"],
        "role_names": [r.name for r in u.roles] if u.roles else ["Job Seeker"],
        "headline": headline,
        "city": city,
        "location": city or "Vietnam",
        "skills": skills,
        "resume_url": resume_url,
        "applications_count": applications_count,
        "status": "active" if u.is_active else "inactive",
        "is_active": u.is_active,
        "is_verified": u.is_verified,
        "is_superuser": u.is_superuser,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "last_login": u.last_login.isoformat() if u.last_login else None,
    }


def serialize_company_user(cu: CompanyUser) -> Dict[str, Any]:
    """Serialize CompanyUser model (Company Employer / Team Member)."""
    company_name = None
    company_tax = None
    if cu.company:
        company_name = cu.company.company_name or cu.company.legal_name
        company_tax = cu.company.tax_code

    role_code = cu.role or "recruiter"
    if role_code == "company_admin":
        role_label = "Company Admin"
    elif role_code == "hiring_manager":
        role_label = "Hiring Manager"
    elif role_code == "interviewer":
        role_label = "Interviewer"
    else:
        role_label = "HR / Recruiter"

    return {
        "id": f"cu_{cu.id}",
        "numeric_id": cu.id,
        "email": cu.email,
        "name": cu.full_name,
        "full_name": cu.full_name,
        "phone": cu.phone,
        "avatar_url": cu.avatar_url,
        "user_type": "company",
        "role": role_label,
        "employee_role": role_code,
        "company_id": cu.company_id,
        "company": company_name,
        "company_name": company_name,
        "tax_code": company_tax,
        "status": "active" if cu.is_active else "inactive",
        "is_active": cu.is_active,
        "is_verified": cu.is_verified,
        "created_at": cu.created_at.isoformat() if cu.created_at else None,
        "last_login": cu.last_login.isoformat() if cu.last_login else None,
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
    """Retrieve paginated platform user accounts with multi-attribute filtering."""
    items: List[Dict[str, Any]] = []

    # If specifically requesting company users
    if user_type in ("company", "company_user", "employer"):
        q = db.query(CompanyUser)
        if search:
            t = f"%{search.strip()}%"
            q = q.join(CompanyUser.company, isouter=True).filter(
                or_(
                    CompanyUser.email.ilike(t),
                    CompanyUser.first_name.ilike(t),
                    CompanyUser.last_name.ilike(t),
                    CompanyProfile.company_name.ilike(t),
                    CompanyProfile.legal_name.ilike(t),
                )
            )
        if status_filter:
            act = True if status_filter.lower() == "active" else False
            q = q.filter(CompanyUser.is_active == act)
        if role and role != "All":
            norm_role = role.lower().replace(" ", "_")
            if "admin" in norm_role:
                q = q.filter(CompanyUser.role == "company_admin")
            elif "hiring" in norm_role:
                q = q.filter(CompanyUser.role == "hiring_manager")
            elif "interviewer" in norm_role:
                q = q.filter(CompanyUser.role == "interviewer")
            else:
                q = q.filter(CompanyUser.role == "recruiter")

        total_items = q.count()
        offset = (page - 1) * page_size
        results = q.order_by(desc(CompanyUser.created_at)).offset(offset).limit(page_size).all()
        return [serialize_company_user(cu) for cu in results], total_items

    # If specifically requesting jobseeker users
    if user_type in ("jobseeker", "candidate"):
        q = db.query(User).filter(User.role_type == "jobseeker")
        if search:
            t = f"%{search.strip()}%"
            q = q.filter(
                or_(
                    User.email.ilike(t),
                    User.first_name.ilike(t),
                    User.last_name.ilike(t),
                )
            )
        if status_filter:
            act = True if status_filter.lower() == "active" else False
            q = q.filter(User.is_active == act)

        total_items = q.count()
        offset = (page - 1) * page_size
        results = q.order_by(desc(User.created_at)).offset(offset).limit(page_size).all()
        return [serialize_user(u) for u in results], total_items

    # Otherwise return combined platform users (Seekers + Company Users)
    seeker_q = db.query(User).filter(User.role_type == "jobseeker")
    company_q = db.query(CompanyUser)

    if search:
        t = f"%{search.strip()}%"
        seeker_q = seeker_q.filter(
            or_(User.email.ilike(t), User.first_name.ilike(t), User.last_name.ilike(t))
        )
        company_q = company_q.join(CompanyUser.company, isouter=True).filter(
            or_(
                CompanyUser.email.ilike(t),
                CompanyUser.first_name.ilike(t),
                CompanyUser.last_name.ilike(t),
                CompanyProfile.company_name.ilike(t),
            )
        )

    if status_filter:
        act = True if status_filter.lower() == "active" else False
        seeker_q = seeker_q.filter(User.is_active == act)
        company_q = company_q.filter(CompanyUser.is_active == act)

    if role and role != "All":
        if role == "Job Seeker":
            company_q = company_q.filter(CompanyUser.id == -1)  # empty
        else:
            seeker_q = seeker_q.filter(User.id == -1)  # empty
            norm_role = role.lower().replace(" ", "_")
            if "admin" in norm_role:
                company_q = company_q.filter(CompanyUser.role == "company_admin")
            elif "hiring" in norm_role:
                company_q = company_q.filter(CompanyUser.role == "hiring_manager")
            elif "interviewer" in norm_role:
                company_q = company_q.filter(CompanyUser.role == "interviewer")
            else:
                company_q = company_q.filter(CompanyUser.role == "recruiter")

    all_seekers = [serialize_user(u) for u in seeker_q.order_by(desc(User.created_at)).all()]
    all_company_users = [serialize_company_user(cu) for cu in company_q.order_by(desc(CompanyUser.created_at)).all()]

    combined = all_seekers + all_company_users
    # Sort by created_at desc
    combined.sort(key=lambda x: x.get("created_at") or "", reverse=True)

    total_items = len(combined)
    offset = (page - 1) * page_size
    paged_items = combined[offset : offset + page_size]

    return paged_items, total_items


@service_error_handler
def get_user_by_id(db: Session, user_id: Any) -> Optional[Any]:
    """Fetch user by id (either User or CompanyUser)."""
    s_id = str(user_id)
    if s_id.startswith("cu_"):
        c_id = int(s_id[3:])
        return db.query(CompanyUser).filter(CompanyUser.id == c_id).first()

    try:
        numeric_id = int(user_id)
        u = db.query(User).filter(User.id == numeric_id).first()
        if u:
            return u
        return db.query(CompanyUser).filter(CompanyUser.id == numeric_id).first()
    except (ValueError, TypeError):
        return None


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
def update_user_record(db: Session, user: Any, data: Dict[str, Any]) -> Any:
    """Update user attributes."""
    if data.get("full_name") is not None:
        user.full_name = data["full_name"]
    if data.get("phone") is not None:
        user.phone = data["phone"]
    if data.get("avatar_url") is not None:
        user.avatar_url = data["avatar_url"]
    if data.get("is_active") is not None:
        user.is_active = data["is_active"]

    if hasattr(user, "roles") and data.get("role_ids") is not None:
        roles = db.query(Role).filter(Role.id.in_(data["role_ids"])).all()
        user.roles = roles

    db.commit()
    db.refresh(user)
    logger.info(f"Admin updated user id={user.id}")
    return user


@service_error_handler
def toggle_user_active_state(db: Session, user: Any) -> bool:
    """Toggle is_active on user or company user."""
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

