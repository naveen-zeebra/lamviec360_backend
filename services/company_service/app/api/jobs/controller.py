# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/jobs/controller.py
# Purpose : Orchestration layer for Company Job Management
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, Dict, Any, Tuple, List
from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from shared.models import User
from shared.utils import log_audit_event
from shared.utils.logger import get_logger

from . import service
from .schemas import CompanyJobCreateRequest, CompanyJobUpdateRequest

logger = get_logger("company_jobs_controller")


def _require_company_profile(user: User):
    profile = service.get_company_tenant(user)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted: No employer organization associated with this tenant account",
        )
    return profile


def list_jobs_controller(
    user: User,
    status_filter: Optional[str],
    page: int,
    page_size: int,
    db: Session,
) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieve paginated jobs belonging to user's company."""
    profile = service.get_company_tenant(user)
    if not profile:
        return [], 0
    return service.list_company_jobs(db, profile.id, status_filter, page, page_size)


def create_job_controller(
    data: CompanyJobCreateRequest,
    user: User,
    request: Request,
    db: Session,
) -> Dict[str, Any]:
    """Create a new job and log an audit event."""
    profile = service.get_or_create_company_tenant(db, user)
    data_dict = data.model_dump() if hasattr(data, "model_dump") else data.dict()
    job = service.create_job_posting(db, profile.id, data_dict)

    log_audit_event(
        db,
        action="CREATE_JOB",
        module="COMPANY_JOBS",
        description=f"Company {profile.company_name} created job '{job.title}' (ID {job.id})",
        user_id=user.id,
        user_email=user.email,
        user_type=user.user_type,
        request=request,
    )

    return {"id": job.id, "title": job.title, "status": job.status}


def get_job_controller(job_id: int, user: User, db: Session) -> Dict[str, Any]:
    """Retrieve single job details."""
    profile = _require_company_profile(user)
    job = service.get_job_by_id(db, profile.id, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")
    return service.serialize_job(job)


def update_job_controller(
    job_id: int,
    data: CompanyJobUpdateRequest,
    user: User,
    db: Session,
) -> Dict[str, Any]:
    """Update job posting."""
    profile = _require_company_profile(user)
    job = service.get_job_by_id(db, profile.id, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")

    data_dict = data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else data.dict(exclude_unset=True)
    updated_job = service.update_job_posting(db, job, data_dict)
    return {"id": updated_job.id, "title": updated_job.title}


def toggle_status_controller(
    job_id: int,
    status_val: str,
    user: User,
    db: Session,
) -> str:
    """Toggle job lifecycle status."""
    profile = _require_company_profile(user)
    job = service.get_job_by_id(db, profile.id, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")
    return service.toggle_job_status(db, job, status_val)


def duplicate_job_controller(job_id: int, user: User, db: Session) -> Dict[str, Any]:
    """Duplicate job posting."""
    profile = _require_company_profile(user)
    source_job = service.get_job_by_id(db, profile.id, job_id)
    if not source_job:
        raise HTTPException(status_code=404, detail="Job posting not found")
    new_job = service.duplicate_job(db, profile.id, source_job)
    return {"id": new_job.id, "title": new_job.title}


def delete_job_controller(job_id: int, user: User, db: Session) -> None:
    """Soft delete job posting."""
    profile = _require_company_profile(user)
    job = service.get_job_by_id(db, profile.id, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")
    service.delete_job(db, job)
