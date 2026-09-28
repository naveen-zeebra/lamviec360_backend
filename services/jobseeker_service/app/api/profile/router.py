# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/profile/router.py
# Purpose : Presentation layer (FastAPI endpoints) for Job Seeker Profile
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import User
from shared.schemas import APIResponse
from shared.utils import require_user_type, success_response

from .schemas import JobSeekerProfileUpdateSchema
from .controller import (
    get_profile_controller,
    update_profile_controller,
    get_saved_jobs_controller,
    save_job_controller,
    unsave_job_controller,
)

router = APIRouter(prefix="/profile", tags=["Job Seeker Profile"])


@router.get("", response_model=APIResponse[dict], summary="Get Job Seeker Profile")
def get_jobseeker_profile(
    user: User = Depends(require_user_type("jobseeker", "super_admin")),
    db: Session = Depends(get_db),
):
    return success_response(data=get_profile_controller(user, db))


@router.put("", response_model=APIResponse[dict], summary="Update Job Seeker Profile")
def update_jobseeker_profile(
    data: JobSeekerProfileUpdateSchema,
    user: User = Depends(require_user_type("jobseeker", "super_admin")),
    db: Session = Depends(get_db),
):
    return success_response(
        data=update_profile_controller(data, user, db),
        message="Profile updated successfully",
    )


@router.get("/saved-jobs", response_model=APIResponse[list], summary="Get Saved Jobs")
def get_saved_jobs(
    user: User = Depends(require_user_type("jobseeker", "super_admin")),
    db: Session = Depends(get_db),
):
    return success_response(data=get_saved_jobs_controller(user, db))


@router.post("/saved-jobs/{job_id}", response_model=APIResponse[dict], summary="Save Job")
def save_job(
    job_id: int,
    user: User = Depends(require_user_type("jobseeker", "super_admin")),
    db: Session = Depends(get_db),
):
    save_job_controller(job_id, user, db)
    return success_response(message="Job saved successfully")


@router.delete("/saved-jobs/{job_id}", response_model=APIResponse[None], summary="Unsave Job")
def unsave_job(
    job_id: int,
    user: User = Depends(require_user_type("jobseeker", "super_admin")),
    db: Session = Depends(get_db),
):
    unsave_job_controller(job_id, user, db)
    return success_response(message="Job removed from saved list")
