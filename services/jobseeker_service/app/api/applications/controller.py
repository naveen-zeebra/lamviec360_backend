# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/applications/controller.py
# Purpose : Orchestration layer for Candidate Job Applications
# ─────────────────────────────────────────────────────────────────────────────

from typing import Dict, Any, List
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from shared.models import User
from shared.utils import log_audit_event
from shared.utils.logger import get_logger

from . import service
from .schemas import JobApplicationCreateRequest

logger = get_logger("jobseeker_applications_controller")


def apply_for_job_controller(
    data: JobApplicationCreateRequest,
    user: User,
    request: Request,
    db: Session,
) -> Dict[str, Any]:
    """Validate vacancy, apply, increment count, and audit event."""
    profile = service.get_or_create_profile(db, user)

    job = service.get_active_job(db, data.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job posting is no longer active or does not exist")

    if service.check_existing_application(db, data.job_id, profile.id):
        raise HTTPException(status_code=400, detail="You have already applied for this position")

    app = service.create_application(
        db=db,
        job=job,
        profile=profile,
        cover_letter=data.cover_letter,
        resume_url=data.resume_url,
    )

    log_audit_event(
        db,
        action="APPLY",
        module="JOB_APPLICATIONS",
        description=f"User {user.email} applied for job '{job.title}' (ID {job.id})",
        user_id=user.id,
        user_email=user.email,
        user_type=user.user_type,
        request=request,
    )

    return {
        "application_id": app.id,
        "job_id": job.id,
        "job_title": job.title,
        "status": app.status,
        "applied_at": app.created_at.isoformat() if app.created_at else None,
    }


def get_my_applications_controller(user: User, db: Session) -> List[Dict[str, Any]]:
    """Retrieve applicant's application history."""
    profile = service.get_or_create_profile(db, user)
    return service.list_my_applications(db, profile.id)


def get_application_detail_controller(application_id: int, user: User, db: Session) -> Dict[str, Any]:
    """Retrieve single application detail."""
    profile = service.get_or_create_profile(db, user)
    detail = service.get_application_by_id(db, application_id, profile.id)
    if not detail:
        raise HTTPException(status_code=404, detail="Application not found")
    return detail
