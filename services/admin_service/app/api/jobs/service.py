# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/jobs/service.py
# Purpose : Domain & database logic for Admin Job Moderation
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from shared.models import JobPosting
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("admin_jobs_service")


def serialize_admin_job_item(j: JobPosting) -> Dict[str, Any]:
    """Serialize job posting for list moderation view."""
    return {
        "id": j.id,
        "title": j.title,
        "company_name": j.company.company_name if j.company else "Unknown",
        "job_type": j.job_type,
        "workplace_type": j.workplace_type,
        "experience_level": j.experience_level,
        "city": j.city,
        "status": j.status,
        "moderation_status": j.moderation_status,
        "views_count": j.views_count,
        "applications_count": j.applications_count,
        "created_at": j.created_at.isoformat() if j.created_at else None,
    }


def serialize_admin_job_detail(j: JobPosting) -> Dict[str, Any]:
    """Serialize full job details for moderation review."""
    return {
        "id": j.id,
        "title": j.title,
        "description": j.description,
        "requirements": j.requirements,
        "benefits": j.benefits,
        "job_type": j.job_type,
        "workplace_type": j.workplace_type,
        "experience_level": j.experience_level,
        "city": j.city,
        "country": j.country,
        "salary_min": float(j.salary_min) if j.salary_min is not None else None,
        "salary_max": float(j.salary_max) if j.salary_max is not None else None,
        "salary_currency": j.salary_currency,
        "status": j.status,
        "moderation_status": j.moderation_status,
        "moderation_notes": j.moderation_notes,
        "views_count": j.views_count,
        "applications_count": j.applications_count,
        "created_at": j.created_at.isoformat() if j.created_at else None,
        "company": {
            "id": j.company.id,
            "name": j.company.company_name,
            "verification_status": j.company.verification_status,
        } if j.company else None,
    }


@service_error_handler
def list_jobs(
    db: Session,
    moderation_status: Optional[str] = None,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieve paginated jobs with moderation filters."""
    query = db.query(JobPosting).filter(JobPosting.is_deleted == False)

    if moderation_status:
        query = query.filter(JobPosting.moderation_status == moderation_status)
    if status_filter:
        query = query.filter(JobPosting.status == status_filter)
    if search:
        query = query.filter(JobPosting.title.ilike(f"%{search.strip()}%"))

    total_items = query.count()
    offset = (page - 1) * page_size
    jobs = query.order_by(desc(JobPosting.created_at)).offset(offset).limit(page_size).all()

    items = [serialize_admin_job_item(j) for j in jobs]
    return items, total_items


@service_error_handler
def get_job_by_id(db: Session, job_id: int) -> Optional[JobPosting]:
    """Fetch active (non-deleted) job posting by ID."""
    return db.query(JobPosting).filter(
        JobPosting.id == job_id,
        JobPosting.is_deleted == False,
    ).first()


@service_error_handler
def moderate_job_post(
    db: Session,
    job: JobPosting,
    moderation_status: str,
    moderation_notes: Optional[str] = None,
) -> JobPosting:
    """Update moderation status and notes for a job post."""
    job.moderation_status = moderation_status
    if moderation_notes is not None:
        job.moderation_notes = moderation_notes

    db.commit()
    db.refresh(job)
    logger.info(f"Admin moderated job id={job.id} status={moderation_status}")
    return job


@service_error_handler
def soft_delete_job_post(db: Session, job: JobPosting) -> None:
    """Soft delete a job posting."""
    job.is_deleted = True
    db.commit()
    logger.info(f"Admin soft-deleted job id={job.id}")
