# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/jobs/service.py
# Purpose : Domain & persistence logic for Company Job Postings
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from shared.models import User, CompanyProfile, JobPosting
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("company_jobs_service")


from ..tenant import get_tenant_profile

@service_error_handler
def get_company_tenant(user: User) -> Optional[CompanyProfile]:
    """Return the associated company profile for a user."""
    from shared.database.session import SessionLocal
    with SessionLocal() as db:
        return get_tenant_profile(db, user)

@service_error_handler
def get_or_create_company_tenant(db: Session, user: User) -> CompanyProfile:
    """Ensure company profile exists before creating jobs."""
    return get_tenant_profile(db, user)


def serialize_job(j: JobPosting) -> Dict[str, Any]:
    """Serialize JobPosting entity to dictionary with frontend compatibility fields."""
    return {
        "id": j.id,
        "title": j.title,
        "job_type": j.job_type,
        "type": j.job_type,
        "workplace_type": j.workplace_type,
        "experience_level": j.experience_level,
        "city": j.city,
        "location": j.city,
        "country": j.country,
        "salary_min": float(j.salary_min) if j.salary_min else None,
        "salary_max": float(j.salary_max) if j.salary_max else None,
        "salary_currency": j.salary_currency,
        "is_negotiable": j.is_negotiable,
        "status": j.status,
        "moderation_status": j.moderation_status,
        "views_count": j.views_count,
        "applications_count": j.applications_count,
        "applicant_count": j.applications_count,
        "deadline": j.expires_at.isoformat() if j.expires_at else None,
        "created_at": j.created_at.isoformat() if j.created_at else None,
        "skills": [s.strip() for s in (j.required_skills or "").split(",") if s.strip()],
        "required_skills": j.required_skills,
        "description": j.description,
        "jd": j.description,
        "requirements": j.requirements,
        "benefits": j.benefits,
    }


@service_error_handler
def list_company_jobs(
    db: Session,
    company_id: int,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> Tuple[List[Dict[str, Any]], int]:
    """Fetch paginated jobs for a specific company."""
    query = db.query(JobPosting).filter(
        JobPosting.company_id == company_id,
        JobPosting.is_deleted == False,
    )
    if status_filter:
        query = query.filter(JobPosting.status == status_filter)

    total_items = query.count()
    offset = (page - 1) * page_size
    jobs = query.order_by(desc(JobPosting.created_at)).offset(offset).limit(page_size).all()

    items = [serialize_job(j) for j in jobs]
    return items, total_items


@service_error_handler
def create_job_posting(db: Session, company_id: int, data: Dict[str, Any]) -> JobPosting:
    """Create a new job posting for the company."""
    raw_status = (data.get("status") or "published").lower()
    init_status = "published" if raw_status in ("active", "published") else raw_status

    job = JobPosting(
        company_id=company_id,
        title=data["title"],
        description=data["description"],
        requirements=data.get("requirements"),
        benefits=data.get("benefits"),
        job_type=data.get("job_type", "full_time"),
        workplace_type=data.get("workplace_type", "on_site"),
        experience_level=data.get("experience_level", "mid"),
        city=data.get("city"),
        country=data.get("country", "Vietnam"),
        salary_min=data.get("salary_min"),
        salary_max=data.get("salary_max"),
        salary_currency=data.get("salary_currency", "VND"),
        is_negotiable=data.get("is_negotiable", False),
        required_skills=data.get("required_skills"),
        status=init_status,
        moderation_status="approved",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info(f"Created job posting id={job.id} for company_id={company_id}")
    return job


@service_error_handler
def get_job_by_id(db: Session, company_id: int, job_id: int) -> Optional[JobPosting]:
    """Find a non-deleted job belonging to this company."""
    return db.query(JobPosting).filter(
        JobPosting.id == job_id,
        JobPosting.company_id == company_id,
        JobPosting.is_deleted == False,
    ).first()


@service_error_handler
def update_job_posting(db: Session, job: JobPosting, data: Dict[str, Any]) -> JobPosting:
    """Update fields on a job posting."""
    for field, value in data.items():
        if hasattr(job, field) and value is not None:
            setattr(job, field, value)
    db.commit()
    db.refresh(job)
    logger.info(f"Updated job posting id={job.id}")
    return job


@service_error_handler
def toggle_job_status(db: Session, job: JobPosting, new_status: str) -> str:
    """Toggle job publication/lifecycle status."""
    norm = new_status.lower()
    if norm == "active":
        norm = "published"
    job.status = norm
    db.commit()
    logger.info(f"Job id={job.id} status changed to {norm}")
    return norm


@service_error_handler
def duplicate_job(db: Session, company_id: int, source_job: JobPosting) -> JobPosting:
    """Duplicate an existing job as a draft."""
    new_job = JobPosting(
        company_id=company_id,
        title=f"{source_job.title} (Copy)",
        description=source_job.description,
        requirements=source_job.requirements,
        benefits=source_job.benefits,
        job_type=source_job.job_type,
        workplace_type=source_job.workplace_type,
        experience_level=source_job.experience_level,
        city=source_job.city,
        country=source_job.country,
        salary_min=source_job.salary_min,
        salary_max=source_job.salary_max,
        salary_currency=source_job.salary_currency,
        is_negotiable=source_job.is_negotiable,
        required_skills=source_job.required_skills,
        status="draft",
        moderation_status="approved",
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    logger.info(f"Duplicated job id={source_job.id} -> new job id={new_job.id}")
    return new_job


@service_error_handler
def delete_job(db: Session, job: JobPosting) -> None:
    """Soft delete a job posting."""
    job.is_deleted = True
    db.commit()
    logger.info(f"Soft-deleted job id={job.id}")
