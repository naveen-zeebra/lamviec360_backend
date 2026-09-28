# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/applicants/router.py
# Purpose : Presentation layer (FastAPI endpoints) for ATS Applicant Management
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import User
from shared.schemas import PaginatedResponse, APIResponse
from shared.utils import require_user_type, success_response, paginated_response

from .schemas import (
    ApplicantStatusUpdateSchema,
    BulkStageRequest,
    CandidateNoteRequest,
    ScheduleInterviewRequest,
)
from .controller import (
    list_applicants_controller,
    get_stage_counts_controller,
    get_applicant_detail_controller,
    update_applicant_status_controller,
    bulk_update_status_controller,
    add_note_controller,
    schedule_interview_controller,
)

router = APIRouter(prefix="/applicants", tags=["ATS Applicant Management"])


@router.get("/stage-counts", response_model=APIResponse[dict], summary="Get ATS Stage Counts")
def get_applicant_stage_counts(
    job_id: Optional[int] = Query(None),
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    counts = get_stage_counts_controller(user, job_id, db)
    return success_response(data=counts, message="Stage counts retrieved")


@router.get("", response_model=PaginatedResponse[dict], summary="List Applicants")
def list_applicants(
    job_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    stage_filter: Optional[str] = Query(None, alias="stage"),
    search: Optional[str] = Query(None),
    min_score: Optional[int] = Query(None),
    sort_by: Optional[str] = Query("date"),
    sort_order: Optional[str] = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    resolved_status = status_filter or stage_filter
    items, total_items = list_applicants_controller(
        user=user,
        job_id=job_id,
        status_filter=resolved_status,
        search=search,
        min_score=min_score,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
        db=db,
    )
    return paginated_response(
        items=items,
        total_items=total_items,
        page=page,
        page_size=page_size,
        message="Applicants retrieved",
    )


@router.get("/{application_id}", response_model=APIResponse[dict], summary="Get Applicant Detail")
def get_applicant_detail(
    application_id: int,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    return success_response(data=get_applicant_detail_controller(application_id, user, db))


@router.patch("/{application_id}/status", response_model=APIResponse[dict], summary="Update Applicant Status")
def update_applicant_status(
    application_id: int,
    data: ApplicantStatusUpdateSchema,
    request: Request,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    result = update_applicant_status_controller(application_id, data, user, request, db)
    return success_response(data=result, message="Applicant status updated successfully")


@router.post("/bulk-stage", response_model=APIResponse[dict], summary="Bulk Update Applicant Stage")
def bulk_update_applicant_status(
    data: BulkStageRequest,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    count = bulk_update_status_controller(data, user, db)
    return success_response(message=f"Bulk updated {count} applicants to {data.status}")


@router.post("/{application_id}/notes", response_model=APIResponse[dict], summary="Add Candidate Note")
def add_candidate_note(
    application_id: int,
    data: CandidateNoteRequest,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    add_note_controller(application_id, data, user, db)
    return success_response(message="Note added successfully")


@router.post("/{application_id}/schedule-interview", response_model=APIResponse[dict], summary="Schedule Interview")
def schedule_candidate_interview(
    application_id: int,
    data: ScheduleInterviewRequest,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    schedule_interview_controller(application_id, data, user, db)
    return success_response(message="Interview scheduled successfully")
