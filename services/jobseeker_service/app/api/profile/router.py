# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/profile/router.py
# Purpose : Presentation layer (FastAPI endpoints) for Job Seeker Profile
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import User
from shared.schemas import APIResponse
from shared.utils import get_current_jobseeker, success_response

from .schemas import JobSeekerProfileUpdateSchema
from .controller import (
    get_profile_controller,
    update_profile_controller,
    get_saved_jobs_controller,
    save_job_controller,
    unsave_job_controller,
)
from . import resume_service
from . import service as profile_service

router = APIRouter(prefix="/profile", tags=["Job Seeker Profile"])


@router.get("", response_model=APIResponse[dict], summary="Get Job Seeker Profile")
def get_jobseeker_profile(
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    return success_response(data=get_profile_controller(user, db))


@router.put("", response_model=APIResponse[dict], summary="Update Job Seeker Profile")
def update_jobseeker_profile(
    data: JobSeekerProfileUpdateSchema,
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    return success_response(
        data=update_profile_controller(data, user, db),
        message="Profile updated successfully",
    )


@router.post("/avatar", response_model=APIResponse[dict], summary="Upload Job Seeker Avatar")
def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    avatar_url = profile_service.save_avatar_file(db, user, file)
    return success_response(
        data={"avatar_url": avatar_url},
        message="Avatar uploaded successfully",
    )


@router.get("/resumes", response_model=APIResponse[dict], summary="List saved résumés")
def list_resumes(
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    profile = profile_service.get_or_create_jobseeker_profile(db, user)
    return success_response(data=resume_service.list_resumes_payload(db, profile))


@router.post("/resumes", response_model=APIResponse[dict], summary="Upload a résumé (max 5)")
def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    profile = profile_service.get_or_create_jobseeker_profile(db, user)
    row = resume_service.add_resume_from_upload(db, profile, file)
    payload = resume_service.list_resumes_payload(db, profile)
    payload["item"] = resume_service.serialize_resume(row)
    return success_response(data=payload, message="Résumé uploaded successfully")


@router.patch("/resumes/{resume_id}/default", response_model=APIResponse[dict], summary="Set default résumé")
def set_default_resume(
    resume_id: int,
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    profile = profile_service.get_or_create_jobseeker_profile(db, user)
    row = resume_service.set_default_resume(db, profile, resume_id)
    payload = resume_service.list_resumes_payload(db, profile)
    payload["item"] = resume_service.serialize_resume(row)
    return success_response(data=payload, message="Default résumé updated")


@router.delete("/resumes/{resume_id}", response_model=APIResponse[dict], summary="Delete a saved résumé")
def delete_resume(
    resume_id: int,
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    profile = profile_service.get_or_create_jobseeker_profile(db, user)
    resume_service.delete_resume(db, profile, resume_id)
    return success_response(data=resume_service.list_resumes_payload(db, profile), message="Résumé removed")


@router.get("/resumes/{resume_id}/download", summary="Download a saved résumé")
def download_resume(
    resume_id: int,
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    profile = profile_service.get_or_create_jobseeker_profile(db, user)
    path, row = resume_service.download_path_for_resume(db, profile, resume_id)
    return FileResponse(path=str(path), filename=row.file_name, media_type=row.mime_type or "application/octet-stream")


@router.get("/completeness", response_model=APIResponse[dict], summary="Get Profile Completeness")
def get_profile_completeness(
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    from . import service
    profile = service.get_or_create_jobseeker_profile(db, user)
    completeness = service.compute_profile_completeness(user, profile)
    return success_response(data={
        "completeness": completeness,
        "can_apply": completeness >= 60,
        "min_required": 60,
    })


@router.get("/saved-jobs", response_model=APIResponse[list], summary="Get Saved Jobs")
def get_saved_jobs(
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    return success_response(data=get_saved_jobs_controller(user, db))


@router.post("/saved-jobs/{job_id}", response_model=APIResponse[dict], summary="Save Job")
def save_job(
    job_id: int,
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    save_job_controller(job_id, user, db)
    return success_response(message="Job saved successfully")


@router.delete("/saved-jobs/{job_id}", response_model=APIResponse[None], summary="Unsave Job")
def unsave_job(
    job_id: int,
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    unsave_job_controller(job_id, user, db)
    return success_response(message="Job removed from saved list")
