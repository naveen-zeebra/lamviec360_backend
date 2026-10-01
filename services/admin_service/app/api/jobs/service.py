# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/jobs/service.py
# Purpose : Domain & database logic for Admin Job Moderation
# ─────────────────────────────────────────────────────────────────────────────

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from shared.models import JobPosting, JobReport
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("admin_jobs_service")


def serialize_admin_job_item(j: JobPosting) -> Dict[str, Any]:
    """Serialize job posting for moderation list and review."""
    reports_list = []
    if hasattr(j, "reports") and j.reports:
        reports_list = [
            {
                "id": r.id,
                "reporter_name": r.reporter_name,
                "reporter_email": r.reporter_email,
                "reason": r.reason,
                "details": r.details,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in j.reports
        ]

    return {
        "id": j.id,
        "title": j.title,
        "description": j.description,
        "requirements": j.requirements,
        "benefits": j.benefits,
        "company_name": j.company.company_name if j.company else "Unknown",
        "company": {
            "id": j.company.id,
            "name": j.company.company_name,
            "verification_status": j.company.verification_status,
        } if j.company else None,
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
        "reports_count": len(reports_list),
        "reports": reports_list,
        "views_count": j.views_count,
        "applications_count": j.applications_count,
        "created_at": j.created_at.isoformat() if j.created_at else None,
    }


def serialize_admin_job_detail(j: JobPosting) -> Dict[str, Any]:
    """Serialize full job details for moderation review."""
    return serialize_admin_job_item(j)



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
    admin_email: Optional[str] = None,
) -> JobPosting:
    """Update moderation status and notes for a job post, and resolve any pending reports."""
    job.moderation_status = moderation_status
    if moderation_notes is not None:
        job.moderation_notes = moderation_notes

    now = datetime.now(timezone.utc)

    # Sync job status and reports based on moderation outcome
    if moderation_status in ("approved", "dismissed"):
        job.moderation_status = "approved"
        if job.status in ("closed", "draft", "flagged"):
            job.status = "published"
        if hasattr(job, "reports") and job.reports:
            for r in job.reports:
                if r.status == "pending":
                    r.status = "dismissed"
                    r.action_note = moderation_notes or "Dismissed by admin"
                    r.actioned_by = admin_email
                    r.actioned_at = now
    elif moderation_status in ("rejected", "actioned", "taken_down"):
        job.moderation_status = "rejected"
        job.status = "closed"
        if hasattr(job, "reports") and job.reports:
            for r in job.reports:
                if r.status == "pending":
                    r.status = "actioned"
                    r.action_note = moderation_notes or "Action taken: listing closed by admin"
                    r.actioned_by = admin_email
                    r.actioned_at = now
    elif moderation_status == "flagged":
        job.moderation_status = "flagged"

    db.commit()
    db.refresh(job)
    logger.info(f"Admin moderated job id={job.id} status={moderation_status}")
    return job


@service_error_handler
def get_job_reports(db: Session, job_id: int) -> List[Dict[str, Any]]:
    """Retrieve all reports for a specific job."""
    reports = db.query(JobReport).filter(JobReport.job_id == job_id).order_by(desc(JobReport.created_at)).all()
    return [
        {
            "id": r.id,
            "job_id": r.job_id,
            "user_id": r.user_id,
            "reporter_name": r.reporter_name,
            "reporter_email": r.reporter_email,
            "reason": r.reason,
            "details": r.details,
            "status": r.status,
            "action_note": r.action_note,
            "actioned_by": r.actioned_by,
            "actioned_at": r.actioned_at.isoformat() if r.actioned_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reports
    ]


@service_error_handler
def soft_delete_job_post(db: Session, job: JobPosting) -> None:
    """Soft delete a job posting."""
    job.is_deleted = True
    db.commit()
    logger.info(f"Admin soft-deleted job id={job.id}")
