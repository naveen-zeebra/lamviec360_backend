# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/companies/service.py
# Purpose : Domain & database logic for Admin Company Management
# ─────────────────────────────────────────────────────────────────────────────

import json
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from shared.models import CompanyProfile
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("admin_companies_service")


def serialize_company_list_item(c: CompanyProfile) -> Dict[str, Any]:
    """Serialize company record for paginated table listing."""
    active_jobs = [j for j in (c.job_postings or []) if j.status in ("active", "published") and not getattr(j, "is_deleted", False)]
    admin_name = c.contact_person or (c.user.full_name if c.user else None) or (c.legal_name or c.company_name)
    admin_email = c.contact_email or (c.user.email if c.user else None) or (f"admin@{c.website.replace('https://', '').replace('http://', '')}" if c.website else None)
    admin_phone = c.contact_phone or (getattr(c.user, "phone", None) if c.user else None)

    return {
        "id": c.id,
        "user_id": c.user_id,
        "company_name": c.company_name,
        "legal_name": c.legal_name,
        "logo_url": c.logo_url,
        "website": c.website,
        "industry": c.industry,
        "company_size": c.company_size,
        "city": c.city,
        "country": c.country,
        "tax_code": c.tax_code,
        "subscription_tier": c.subscription_tier or "Freemium",
        "admin_name": admin_name,
        "admin_email": admin_email,
        "admin_phone": admin_phone,
        "verification_status": c.verification_status,
        "verification_notes": c.verification_notes,
        "is_featured": c.is_featured,
        "active_jobs_count": len(active_jobs),
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def serialize_company_detail(c: CompanyProfile) -> Dict[str, Any]:
    """Serialize complete company details for admin review."""
    active_jobs = [j for j in (c.job_postings or []) if not getattr(j, "is_deleted", False)]
    admin_name = c.contact_person or (c.user.full_name if c.user else None) or (c.legal_name or c.company_name)
    admin_email = c.contact_email or (c.user.email if c.user else None) or (f"admin@{c.website.replace('https://', '').replace('http://', '')}" if c.website else None)
    admin_phone = c.contact_phone or (getattr(c.user, "phone", None) if c.user else None)

    # Postings
    postings = []
    for j in active_jobs:
        sal = "Competitive"
        if j.salary_min and j.salary_max:
            sal = f"{int(j.salary_min):,} - {int(j.salary_max):,} {j.salary_currency or 'VND'}"
        elif j.salary_min:
            sal = f"From {int(j.salary_min):,} {j.salary_currency or 'VND'}"

        status_label = "Active"
        if j.status == "closed":
            status_label = "Closed"
        elif j.status == "draft":
            status_label = "Draft"
        elif getattr(j, "moderation_status", "") == "rejected":
            status_label = "Flagged"

        postings.append({
            "id": str(j.id),
            "title": j.title,
            "location": j.city or (f"{c.city}, {c.country}" if c.city else "Vietnam"),
            "type": j.job_type or "Full-time",
            "salary": sal,
            "status": status_label,
            "views": getattr(j, "views_count", 0) or 0,
            "applicants": getattr(j, "applications_count", 0) or (len(j.applications) if hasattr(j, "applications") and j.applications else 0),
            "postedAt": j.created_at.strftime("%Y-%m-%d") if j.created_at else "",
        })

    # Team members from settings
    members = []
    settings_data = {}
    if c.settings:
        if isinstance(c.settings, dict):
            settings_data = c.settings
        else:
            try:
                settings_data = json.loads(c.settings)
            except Exception:
                pass

    if isinstance(settings_data.get("team_members"), list) and len(settings_data["team_members"]) > 0:
        for m in settings_data["team_members"]:
            members.append({
                "id": str(m.get("id", "")),
                "name": m.get("name", "Team Member"),
                "email": m.get("email", ""),
                "role": m.get("role", "Company Admin"),
                "joinedAt": m.get("joinDate", m.get("joinedAt", "")),
            })
    elif c.user:
        members.append({
            "id": str(c.user.id),
            "name": c.user.full_name or "Company Admin",
            "email": c.user.email,
            "role": "Company Admin",
            "joinedAt": c.user.created_at.strftime("%Y-%m-%d") if c.user.created_at else "",
        })

    return {
        "id": c.id,
        "user_id": c.user_id,
        "company_name": c.company_name,
        "legal_name": c.legal_name,
        "logo_url": c.logo_url,
        "cover_image_url": c.cover_image_url,
        "tagline": getattr(c, "tagline", "") or "",
        "is_public": getattr(c, "is_public", True) if getattr(c, "is_public", True) is not None else True,
        "website": c.website,
        "industry": c.industry,
        "company_size": c.company_size,
        "about": c.about,
        "benefits": c.benefits or "",
        "address": c.address,
        "city": c.city,
        "country": c.country,
        "tax_code": c.tax_code,
        "subscription_tier": c.subscription_tier or "Freemium",
        "admin_name": admin_name,
        "admin_email": admin_email,
        "admin_phone": admin_phone,
        "verification_status": c.verification_status,
        "verification_notes": c.verification_notes,
        "is_featured": c.is_featured,
        "active_jobs_count": len([j for j in active_jobs if j.status in ("active", "published")]),
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "postings": postings,
        "members": members,
    }


@service_error_handler
def list_companies(
    db: Session,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> Tuple[List[Dict[str, Any]], int]:
    """Query paginated companies with status filter and search term."""
    query = db.query(CompanyProfile)
    if status_filter:
        query = query.filter(CompanyProfile.verification_status == status_filter)
    if search:
        query = query.filter(CompanyProfile.company_name.ilike(f"%{search.strip()}%"))

    total_items = query.count()
    offset = (page - 1) * page_size
    companies = query.order_by(desc(CompanyProfile.created_at)).offset(offset).limit(page_size).all()

    items = [serialize_company_list_item(c) for c in companies]
    return items, total_items


@service_error_handler
def get_company_by_id(db: Session, company_id: int) -> Optional[CompanyProfile]:
    """Fetch company profile by primary key ID."""
    return db.query(CompanyProfile).filter(CompanyProfile.id == company_id).first()


@service_error_handler
def update_company_verification(
    db: Session,
    company: CompanyProfile,
    verification_status: str,
    verification_notes: Optional[str] = None,
    is_featured: Optional[bool] = None,
) -> CompanyProfile:
    """Update verification status, notes, and featured status."""
    company.verification_status = verification_status
    if verification_notes is not None:
        company.verification_notes = verification_notes
    if is_featured is not None:
        company.is_featured = is_featured

    db.commit()
    db.refresh(company)
    logger.info(f"Updated company id={company.id} status={verification_status}")
    return company


@service_error_handler
def toggle_company_feature_status(db: Session, company: CompanyProfile) -> bool:
    """Toggle is_featured boolean flag."""
    company.is_featured = not company.is_featured
    db.commit()
    db.refresh(company)
    logger.info(f"Toggled featured status on company id={company.id} -> {company.is_featured}")
    return company.is_featured


@service_error_handler
def update_company_details(
    db: Session,
    company: CompanyProfile,
    data_dict: Dict[str, Any],
) -> CompanyProfile:
    """Update company details from super admin."""
    name = data_dict.get("company_name") or data_dict.get("name")
    if name is not None:
        company.company_name = name

    if "legal_name" in data_dict:
        company.legal_name = data_dict["legal_name"]

    tax = data_dict.get("tax_code") or data_dict.get("reg_number") or data_dict.get("regNumber")
    if tax is not None:
        company.tax_code = tax

    if "industry" in data_dict:
        company.industry = data_dict["industry"]

    size = data_dict.get("company_size") or data_dict.get("size")
    if size is not None:
        company.company_size = size

    if "website" in data_dict:
        company.website = data_dict["website"]

    if "address" in data_dict:
        company.address = data_dict["address"]

    if "city" in data_dict:
        company.city = data_dict["city"]

    if "country" in data_dict:
        company.country = data_dict["country"]

    abt = data_dict.get("about") or data_dict.get("description")
    if abt is not None:
        company.about = abt

    if "tagline" in data_dict:
        company.tagline = data_dict["tagline"]

    if "benefits" in data_dict:
        company.benefits = data_dict["benefits"]

    admin_person = data_dict.get("contact_person") or data_dict.get("adminName")
    if admin_person is not None:
        company.contact_person = admin_person

    admin_mail = data_dict.get("contact_email") or data_dict.get("adminEmail")
    if admin_mail is not None:
        company.contact_email = admin_mail

    admin_ph = data_dict.get("contact_phone") or data_dict.get("adminPhone")
    if admin_ph is not None:
        company.contact_phone = admin_ph

    if "is_featured" in data_dict and data_dict["is_featured"] is not None:
        company.is_featured = bool(data_dict["is_featured"])

    is_pub = data_dict.get("is_public") if "is_public" in data_dict else data_dict.get("isPublic")
    if is_pub is not None:
        company.is_public = bool(is_pub)

    if "verification_status" in data_dict and data_dict["verification_status"]:
        company.verification_status = data_dict["verification_status"]

    db.commit()
    db.refresh(company)
    logger.info(f"Super Admin updated company id={company.id} name='{company.company_name}'")
    return company

