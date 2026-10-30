# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/companies/service.py
# Purpose : Domain & data retrieval for public Company Discovery & Showcase
# ─────────────────────────────────────────────────────────────────────────────

import json
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from shared.models import CompanyProfile, JobPosting
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("jobseeker_companies_service")


def parse_json_safely(raw: Any) -> Dict[str, Any]:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return {}


def serialize_public_company_summary(c: CompanyProfile, live_jobs_count: int) -> Dict[str, Any]:
    return {
        "id": c.id,
        "name": c.company_name,
        "company_name": c.company_name,
        "legal_name": c.legal_name,
        "logo_url": c.logo_url,
        "cover_image_url": c.cover_image_url,
        "tagline": getattr(c, "tagline", "") or "",
        "industry": c.industry or "Technology",
        "company_size": c.company_size or "11–50 employees",
        "city": c.city or "Vietnam",
        "country": c.country or "Vietnam",
        "website": c.website,
        "verified": c.verification_status == "verified",
        "is_featured": bool(c.is_featured),
        "open_jobs_count": live_jobs_count,
        "about": c.about or "",
    }


def serialize_public_job(j: JobPosting, c: Optional[CompanyProfile] = None) -> Dict[str, Any]:
    sal = "Negotiable"
    salary_type = getattr(j, "salary_type", "Gross") or "Gross"
    if j.salary_min and j.salary_max:
        if (j.salary_currency or "VND") == "VND":
            sal = f"{round(j.salary_min / 1_000_000)}M – {round(j.salary_max / 1_000_000)}M VND ({salary_type})"
        else:
            sal = f"{int(j.salary_min):,} – {int(j.salary_max):,} {j.salary_currency} ({salary_type})"
    elif j.salary_min:
        sal = f"From {int(j.salary_min):,} {j.salary_currency or 'VND'} ({salary_type})"

    skills_list = []
    raw_skills = getattr(j, "required_skills", None) or getattr(j, "skills", None)
    if raw_skills:
        if isinstance(raw_skills, list):
            skills_list = raw_skills
        elif isinstance(raw_skills, str):
            skills_list = [s.strip() for s in raw_skills.split(",") if s.strip()]

    comp_name = c.company_name if c else "Company"
    comp_id = c.id if c else j.company_id
    comp_logo = c.logo_url if c else None
    comp_city = c.city if c else ""

    loc = getattr(j, "location", None) or (
        f"{j.city}, {j.country}" if j.city and j.country else (j.city or j.country or comp_city or "Vietnam")
    )
    dept = getattr(j, "department", "") or getattr(j, "industry", "") or (c.industry if c else "") or "Engineering"

    return {
        "id": j.id,
        "title": j.title,
        "company": comp_name,
        "company_name": comp_name,
        "company_id": comp_id,
        "company_logo": comp_logo,
        "department": dept,
        "location": loc,
        "city": j.city or comp_city or "Vietnam",
        "country": j.country or "Vietnam",
        "job_type": j.job_type or "Full-time",
        "type": j.job_type or "Full-time",
        "workplace_type": j.workplace_type or "On-site",
        "mode": j.workplace_type or "On-site",
        "experience_level": j.experience_level or "Mid-level",
        "salary": sal,
        "salary_min": float(j.salary_min) if j.salary_min is not None else None,
        "salary_max": float(j.salary_max) if j.salary_max is not None else None,
        "salary_currency": j.salary_currency or "VND",
        "salary_type": salary_type,
        "skills": skills_list,
        "required_skills": ", ".join(skills_list) if skills_list else "",
        "posted": j.created_at.strftime("%Y-%m-%d") if j.created_at else "Recently",
        "deadline": j.expires_at.strftime("%Y-%m-%d") if getattr(j, "expires_at", None) else None,
        "description": j.description or "",
    }


@service_error_handler
def list_public_companies(
    db: Session,
    search: Optional[str] = None,
    industry: Optional[str] = None,
    city: Optional[str] = None,
    verified_only: bool = False,
    featured_only: bool = False,
    page: int = 1,
    page_size: int = 12,
) -> Tuple[List[Dict[str, Any]], int]:
    query = db.query(CompanyProfile)

    # Only show public profiles
    query = query.filter(or_(CompanyProfile.is_public == True, CompanyProfile.is_public.is_(None)))

    if verified_only:
        query = query.filter(CompanyProfile.verification_status == "verified")

    if featured_only:
        query = query.filter(CompanyProfile.is_featured == True)

    if industry and industry.lower() != "all":
        query = query.filter(CompanyProfile.industry.ilike(f"%{industry.strip()}%"))

    if city and city.lower() != "all":
        query = query.filter(CompanyProfile.city.ilike(f"%{city.strip()}%"))

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                CompanyProfile.company_name.ilike(s),
                CompanyProfile.legal_name.ilike(s),
                CompanyProfile.about.ilike(s),
                getattr(CompanyProfile, "tagline", CompanyProfile.company_name).ilike(s),
            )
        )

    total_items = query.count()
    offset = (page - 1) * page_size
    companies = (
        query.order_by(
            desc(CompanyProfile.is_featured),
            desc(CompanyProfile.created_at),
        )
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = []
    for c in companies:
        live_jobs = [
            j
            for j in (c.job_postings or [])
            if j.status in ("published", "active")
            and not getattr(j, "is_deleted", False)
            and getattr(j, "moderation_status", "approved") == "approved"
        ]
        items.append(serialize_public_company_summary(c, len(live_jobs)))

    return items, total_items


@service_error_handler
def get_public_company_by_id_or_slug(
    db: Session,
    id_or_slug: str,
) -> Optional[Dict[str, Any]]:
    c = None
    target = str(id_or_slug).strip()
    if target.isdigit():
        c = db.query(CompanyProfile).filter(CompanyProfile.id == int(target)).first()

    if not c:
        c = db.query(CompanyProfile).filter(CompanyProfile.company_name.ilike(target)).first()

    if not c and "-" in target:
        c = db.query(CompanyProfile).filter(CompanyProfile.company_name.ilike(target.replace("-", " "))).first()

    if not c:
        return None

    # Parse tenant settings for culture and workplace config
    settings = parse_json_safely(c.settings)
    culture_values = settings.get("culture_values") or [
        {"title": "Innovation & Impact", "description": "We build scalable, mission-critical digital products that solve real problems.", "icon": "zap"},
        {"title": "People & Growth", "description": "Continuous career mentorship, learning allowances, and an inclusive merit-based culture.", "icon": "users"},
        {"title": "Integrity & Excellence", "description": "Transparent communication, high engineering standards, and shared ownership.", "icon": "shield"},
    ]
    workplace_model = settings.get("workplace_model") or "Hybrid (Flexible remote work options)"
    working_hours = settings.get("working_hours") or "Monday – Friday (9:00 AM – 6:00 PM)"

    # Filter live jobs
    live_jobs = [
        serialize_public_job(j, c)
        for j in (c.job_postings or [])
        if j.status in ("published", "active")
        and not getattr(j, "is_deleted", False)
        and getattr(j, "moderation_status", "approved") == "approved"
    ]

    is_pub = getattr(c, "is_public", True)
    if is_pub is None:
        is_pub = True

    return {
        "id": c.id,
        "name": c.company_name,
        "company_name": c.company_name,
        "legal_name": c.legal_name,
        "logo_url": c.logo_url,
        "cover_image_url": c.cover_image_url,
        "tagline": getattr(c, "tagline", "") or "",
        "industry": c.industry or "Technology",
        "company_size": c.company_size or "11–50 employees",
        "city": c.city or "Vietnam",
        "country": c.country or "Vietnam",
        "address": c.address or f"{c.city or 'Vietnam'}",
        "website": c.website,
        "contact_email": c.contact_email or (c.user.email if c.user else None),
        "contact_phone": c.contact_phone,
        "contact_person": c.contact_person,
        "founded_year": c.founded_year,
        "linkedin_url": c.linkedin_url,
        "facebook_url": c.facebook_url,
        "about": c.about or "",
        "benefits": c.benefits or "",
        "verified": c.verification_status == "verified",
        "is_featured": bool(c.is_featured),
        "is_public": is_pub,
        "workplace_model": workplace_model,
        "working_hours": working_hours,
        "culture_values": culture_values,
        "open_jobs": live_jobs,
        "open_jobs_count": len(live_jobs),
    }
