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
    search: Optional[str],
    min_score: Optional[int],
    min_experience: Optional[float],
    max_experience: Optional[float],
    sort_by: Optional[str],
    sort_order: Optional[str],
    page: int,
    page_size: int,
    db: Session,
) -> Tuple[List[Dict[str, Any]], int]:
    """List paginated candidates with multi-attribute search and sorting."""
    profile = _require_company_profile(user)
    return service.list_company_applicants(
        db=db,
        company_id=profile.id,
        job_id=job_id,
        status_filter=status_filter,
        search=search,
        min_score=min_score,
        min_experience=min_experience,
        max_experience=max_experience,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


def export_applicants_csv_controller(
    user: User,
    job_id: Optional[int],
    status_filter: Optional[str],
    search: Optional[str],
    min_score: Optional[int],
    min_experience: Optional[float],
    max_experience: Optional[float],
    db: Session,
) -> str:
    """Export filtered applicant pool as CSV."""
    profile = _require_company_profile(user)
    return service.export_company_applicants_csv(
        db=db,
        company_id=profile.id,
        job_id=job_id,
        status_filter=status_filter,
        search=search,
        min_score=min_score,
        min_experience=min_experience,
        max_experience=max_experience,
    )


def get_stage_counts_controller(user: User, job_id: Optional[int], db: Session) -> Dict[str, int]:
    """Retrieve stage counts for company ATS pipeline."""
    profile = _require_company_profile(user)
    return service.get_company_stage_counts(db=db, company_id=profile.id, job_id=job_id)


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


def bulk_update_status_controller(
    data: BulkStageRequest,
    user: User,
    db: Session,
    request: Optional[Request] = None,
) -> int:
    """Bulk update multiple candidate stages and log audit trail."""
    profile = _require_company_profile(user)
    count = service.bulk_update_applicant_stage(
        db=db,
        company_id=profile.id,
        application_ids=data.application_ids,
        status=data.status,
        rejection_note=data.rejection_note,
    )
    log_audit_event(
        db,
        action="BULK_UPDATE_APPLICANT_STAGE",
        module="ATS",
        description=f"Bulk updated {count} applicant(s) to status '{data.status}'",
        user_id=user.id,
        user_email=user.email,
        user_type=getattr(user, "user_type", "company"),
        request=request,
        details={"application_ids": data.application_ids, "status": data.status, "count": count},
    )
    return count


def add_note_controller(
    application_id: int,
    data: CandidateNoteRequest,
    user: User,
    db: Session,
    request: Optional[Request] = None,
) -> None:
    """Add note to applicant and log audit trail."""
    profile = _require_company_profile(user)
    app = service.get_applicant_by_id(db, profile.id, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Applicant record not found")
    service.add_candidate_recruiter_note(db, app, data.text)
    log_audit_event(
        db,
        action="ADD_CANDIDATE_NOTE",
        module="ATS",
        description=f"Added internal note to candidate application {application_id}",
        user_id=user.id,
        user_email=user.email,
        user_type=getattr(user, "user_type", "company"),
        request=request,
    )


def schedule_interview_controller(
    application_id: int,
    data: ScheduleInterviewRequest,
    user: User,
    db: Session,
    request: Optional[Request] = None,
) -> None:
    """Schedule candidate interview, notify, and log audit trail."""
    profile = _require_company_profile(user)
    app = service.get_applicant_by_id(db, profile.id, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Applicant record not found")
    service.schedule_candidate_interview(db, app, data.model_dump())
    log_audit_event(
        db,
        action="SCHEDULE_INTERVIEW",
        module="ATS",
        description=f"Scheduled interview for candidate application {application_id} ({data.interview_type} at {data.scheduled_at})",
        user_id=user.id,
        user_email=user.email,
        user_type=getattr(user, "user_type", "company"),
        request=request,
        details=data.model_dump(),
    )


def get_applicant_verification_documents_controller(application_id: int, user: User, db: Session) -> Dict[str, Any]:
    """Retrieve applicant verification documents enforcing EMP-FR-026b visibility rule."""
    profile = _require_company_profile(user)
    return service.get_applicant_verification_documents(db, profile.id, application_id)


def download_applicant_verification_document_controller(
    application_id: int,
    doc_id: int,
    user: User,
    db: Session,
    request: Optional[Request] = None,
) -> Tuple[bytes, Any]:
    """Decrypt and download verification document enforcing EMP-FR-026b visibility rule with audit trail."""
    profile = _require_company_profile(user)
    result = service.download_applicant_verification_document(db, profile.id, application_id, doc_id)
    log_audit_event(
        db,
        action="DOWNLOAD_VERIFICATION_DOCUMENT",
        module="ATS",
        description=f"Downloaded verification document ID {doc_id} for applicant {application_id}",
        user_id=user.id,
        user_email=user.email,
        user_type=getattr(user, "user_type", "company"),
        request=request,
    )
    return result
