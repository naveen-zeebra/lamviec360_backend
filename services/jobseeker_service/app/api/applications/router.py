# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/applications/router.py
# Purpose : Presentation layer (FastAPI endpoints) for Candidate Job Applications
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import User
from shared.schemas import APIResponse
from shared.utils import get_current_jobseeker, success_response

from .schemas import JobApplicationCreateRequest
from .controller import (
    apply_for_job_controller,
    get_my_applications_controller,
    get_application_detail_controller,
)

router = APIRouter(prefix="/applications", tags=["Job Applications"])


@router.post("", response_model=APIResponse[dict], summary="Apply for Job")
def apply_for_job(
    data: JobApplicationCreateRequest,
    request: Request,
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    result = apply_for_job_controller(data, user, request, db)
    return success_response(
        data=result,
        message="Application submitted successfully!",
    )


@router.get("", response_model=APIResponse[list], summary="Get My Applications")
def get_my_applications(
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    return success_response(data=get_my_applications_controller(user, db))


@router.get("/{application_id}", response_model=APIResponse[dict], summary="Get Application Details")
def get_application_detail(
    application_id: int,
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    return success_response(data=get_application_detail_controller(application_id, user, db))
