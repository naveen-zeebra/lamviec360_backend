# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/companies/service.py
# Purpose : Domain & database logic for Admin Company Management
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from shared.models import CompanyProfile
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("admin_companies_service")


def serialize_company_list_item(c: CompanyProfile) -> Dict[str, Any]:
    """Serialize company record for paginated table listing."""
    active_jobs = [j for j in (c.job_postings or []) if j.status == "active" and not getattr(j, "is_deleted", False)]
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
        "verification_status": c.verification_status,
        "is_featured": c.is_featured,
        "active_jobs_count": len(active_jobs),
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def serialize_company_detail(c: CompanyProfile) -> Dict[str, Any]:
    """Serialize complete company details for admin review."""
    return {
        "id": c.id,
        "user_id": c.user_id,
        "company_name": c.company_name,
        "legal_name": c.legal_name,
        "logo_url": c.logo_url,
        "cover_image_url": c.cover_image_url,
        "website": c.website,
        "industry": c.industry,
        "company_size": c.company_size,
        "about": c.about,
        "address": c.address,
        "city": c.city,
        "country": c.country,
        "verification_status": c.verification_status,
        "verification_notes": c.verification_notes,
        "is_featured": c.is_featured,
        "created_at": c.created_at.isoformat() if c.created_at else None,
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
