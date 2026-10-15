# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/applications/router.py
# Purpose : Presentation layer (FastAPI endpoints) for Candidate Job Applications
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
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
    withdraw_application_controller,
)

router = APIRouter(prefix="/applications", tags=["Job Applications"])


def _truthy(value) -> bool:
    if value is None or value == "":
        return True
    return str(value).strip().lower() in ("1", "true", "yes", "on")


@router.post("", response_model=APIResponse[dict], summary="Apply for Job")
async def apply_for_job(
    request: Request,
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    content_type = (request.headers.get("content-type") or "").lower()
    upload_file = None
    if "multipart/form-data" in content_type:
        form = await request.form()
        job_id_raw = form.get("job_id")
        if job_id_raw in (None, ""):
            raise HTTPException(status_code=400, detail="job_id is required")
        resume_id_raw = form.get("resume_id")
        data = JobApplicationCreateRequest(
            job_id=int(job_id_raw),
            cover_letter=form.get("cover_letter") or None,
            resume_url=form.get("resume_url") or None,
            resume_id=int(resume_id_raw) if resume_id_raw not in (None, "") else None,
            save_to_profile=_truthy(form.get("save_to_profile")),
        )
        file_field = form.get("file")
        if file_field is not None and getattr(file_field, "filename", None):
            upload_file = file_field
    else:
        try:
            body = await request.json()
            data = JobApplicationCreateRequest(**body)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors())
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid application payload")

    result = apply_for_job_controller(data, user, request, db, upload_file=upload_file)
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


@router.post("/{application_id}/withdraw", response_model=APIResponse[dict], summary="Withdraw Job Application")
def withdraw_application(
    application_id: int,
    request: Request,
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    result = withdraw_application_controller(application_id, user, request, db)
    return success_response(
        data=result,
        message="Application withdrawn successfully.",
    )
