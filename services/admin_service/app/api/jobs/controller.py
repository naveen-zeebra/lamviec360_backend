# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/jobs/controller.py
# Purpose : Orchestration layer for Admin Job Moderation
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session

from shared.models import User
from shared.utils import log_audit_event
from shared.utils.logger import get_logger
from .schemas import JobModerationSchema
from .service import (
    list_jobs,
    get_job_by_id,
    moderate_job_post,
    soft_delete_job_post,
    serialize_admin_job_detail,
)

logger = get_logger("admin_jobs_controller")


def list_jobs_controller(
    db: Session,
    moderation_status: Optional[str] = None,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieve filtered and paginated jobs for moderation."""
    return list_jobs(
        db=db,
        moderation_status=moderation_status,
        status_filter=status_filter,
        search=search,
        page=page,
        page_size=page_size,
    )


def get_job_detail_controller(db: Session, job_id: int) -> Dict[str, Any]:
    """Retrieve detailed information for a single job posting."""
    job = get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found",
        )
    return serialize_admin_job_detail(job)


def moderate_job_controller(
    db: Session,
    job_id: int,
    data: JobModerationSchema,
    current_admin: User,
    request: Optional[Request] = None,
) -> Dict[str, Any]:
    """Approve, reject, or flag a job posting for review."""
    job = get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found",
        )

    updated = moderate_job_post(
        db=db,
        job=job,
        moderation_status=data.moderation_status,
        moderation_notes=data.moderation_notes,
    )

    log_audit_event(
        db,
        action="MODERATE_JOB",
        module="ADMIN_JOBS",
        description=f"Admin {current_admin.email} moderated job '{updated.title}' to {data.moderation_status}",
        user_id=current_admin.id,
        user_email=current_admin.email,
        user_type=current_admin.user_type,
        request=request,
    )

    return {"id": updated.id, "moderation_status": updated.moderation_status}


def delete_job_controller(
    db: Session,
    job_id: int,
    current_admin: User,
    request: Optional[Request] = None,
) -> None:
    """Soft-delete a job posting."""
    job = get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found",
        )

    soft_delete_job_post(db, job)

    log_audit_event(
        db,
        action="DELETE_JOB",
        module="ADMIN_JOBS",
        description=f"Admin {current_admin.email} removed job '{job.title}'",
        user_id=current_admin.id,
        user_email=current_admin.email,
        user_type=current_admin.user_type,
        request=request,
    )
