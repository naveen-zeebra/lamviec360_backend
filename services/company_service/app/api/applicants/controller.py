# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/applicants/controller.py
# Purpose : Orchestration layer for ATS Applicant Management
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, Dict, Any, Tuple, List
from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from shared.models import User
from shared.utils import log_audit_event
from shared.utils.logger import get_logger

from . import service
from .schemas import (
    ApplicantStatusUpdateSchema,
    BulkStageRequest,
    CandidateNoteRequest,
    ScheduleInterviewRequest,
)

logger = get_logger("company_applicants_controller")


def _require_company_profile(user: User):
    profile = service.get_company_tenant(user)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted: No employer organization associated with this tenant account",
        )
    return profile


def list_applicants_controller(
    user: User,
    job_id: Optional[int],
    status_filter: Optional[str],
    page: int,
    page_size: int,
    db: Session,
) -> Tuple[List[Dict[str, Any]], int]:
    """List paginated candidates."""
    profile = _require_company_profile(user)
    return service.list_company_applicants(db, profile.id, job_id, status_filter, page, page_size)


def get_applicant_detail_controller(application_id: int, user: User, db: Session) -> Dict[str, Any]:
    """Get full applicant profile and application."""
    profile = _require_company_profile(user)
    app = service.get_applicant_by_id(db, profile.id, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Applicant record not found")
    return service.serialize_applicant_detail(app)


def update_applicant_status_controller(
    application_id: int,
    data: ApplicantStatusUpdateSchema,
    user: User,
    request: Request,
    db: Session,
) -> Dict[str, Any]:
    """Update applicant stage and log audit event."""
    profile = _require_company_profile(user)
    app = service.get_applicant_by_id(db, profile.id, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Applicant record not found")

    updated = service.update_applicant_status_and_notes(
        db=db,
        app=app,
        status=data.status,
        notes=data.recruiter_notes,
        rating=data.rating,
    )

    log_audit_event(
        db,
        action="UPDATE_APPLICANT_STATUS",
        module="ATS",
        description=f"Candidate application {application_id} updated to status '{data.status}'",
        user_id=user.id,
        user_email=user.email,
        user_type=user.user_type,
        request=request,
    )

    return {"id": updated.id, "status": updated.status, "rating": updated.rating}


def bulk_update_status_controller(data: BulkStageRequest, user: User, db: Session) -> int:
    """Bulk update multiple candidate stages."""
    profile = _require_company_profile(user)
    return service.bulk_update_applicant_stage(
        db=db,
        company_id=profile.id,
        application_ids=data.application_ids,
        status=data.status,
        rejection_note=data.rejection_note,
    )


def add_note_controller(application_id: int, data: CandidateNoteRequest, user: User, db: Session) -> None:
    """Add note to applicant."""
    profile = _require_company_profile(user)
    app = service.get_applicant_by_id(db, profile.id, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Applicant record not found")
    service.add_candidate_recruiter_note(db, app, data.text)


def schedule_interview_controller(
    application_id: int,
    data: ScheduleInterviewRequest,
    user: User,
    db: Session,
) -> None:
    """Schedule interview round with candidate."""
    profile = _require_company_profile(user)
    app = service.get_applicant_by_id(db, profile.id, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Applicant record not found")
    interview_dict = data.model_dump() if hasattr(data, "model_dump") else data.dict()
    service.schedule_candidate_interview(db, app, interview_dict)
