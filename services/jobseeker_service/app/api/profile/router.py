# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/profile/router.py
# Purpose : Presentation layer (FastAPI endpoints) for Job Seeker Profile
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
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
from . import document_service
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


@router.get("/upload-config", response_model=APIResponse[dict], summary="Get upload file size and type configurations")
def get_upload_config():
    from shared.config.upload_config import UPLOAD_CONFIG
    return success_response(
        data=UPLOAD_CONFIG.to_frontend_dict(),
        message="Upload configuration retrieved successfully",
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
    payload["item"] = resume_service.serialize_resume(row, db=db)
    return success_response(data=payload, message="Default résumé updated")


@router.patch("/resumes/{resume_id}", response_model=APIResponse[dict], summary="Rename a saved résumé")
def rename_resume_endpoint(
    resume_id: int,
    data: dict,
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    profile = profile_service.get_or_create_jobseeker_profile(db, user)
    new_name = data.get("resume_name") or data.get("name") or ""
    row = resume_service.rename_resume(db, profile, resume_id, new_name)
    payload = resume_service.list_resumes_payload(db, profile)
    payload["item"] = resume_service.serialize_resume(row, db=db)
    return success_response(data=payload, message="Résumé renamed successfully")



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
    return FileResponse(
        path=str(path),
        filename=row.file_name,
        media_type=row.mime_type or "application/octet-stream",
        content_disposition_type="attachment",
    )



@router.get("/completeness", response_model=APIResponse[dict], summary="Get Profile Completeness")
def get_profile_completeness(
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    from . import service
    profile = service.get_or_create_jobseeker_profile(db, user)
    details = service.get_profile_completeness_details(user, profile)
    return success_response(data=details)



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


# ─── JSP-FR-012: Candidate Document Archive ─────────────────────────────────

@router.get("/documents", response_model=APIResponse[dict], summary="List archived documents & quota")
def list_candidate_documents(
    category: str = "all",
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    profile = profile_service.get_or_create_jobseeker_profile(db, user)
    return success_response(data=document_service.list_documents(db, profile, category=category))


@router.post("/documents", response_model=APIResponse[dict], summary="Upload document to archive (max 10MB)")
async def upload_candidate_document(
    request: Request,
    file: UploadFile = File(...),
    category: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    resolved_category = (category or request.query_params.get("category") or "other").strip().lower()
    resolved_title = title if title is not None else (request.query_params.get("title") or "")
    profile = profile_service.get_or_create_jobseeker_profile(db, user)
    row = document_service.add_document(db, profile, file, category=resolved_category, title=resolved_title)
    usage = document_service.get_archive_usage(db, profile.id)
    return success_response(
        data={"item": document_service.serialize_document(row), "usage": usage},
        message="Document uploaded to archive successfully.",
    )


@router.delete("/documents/{doc_id}", response_model=APIResponse[dict], summary="Delete archived document")
def delete_candidate_document(
    doc_id: int,
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    profile = profile_service.get_or_create_jobseeker_profile(db, user)
    document_service.delete_document(db, profile, doc_id)
    usage = document_service.get_archive_usage(db, profile.id)
    return success_response(data={"usage": usage}, message="Document deleted successfully.")


@router.get("/documents/{doc_id}/download", summary="Download archived document")
def download_candidate_document(
    doc_id: int,
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    profile = profile_service.get_or_create_jobseeker_profile(db, user)
    path, row = document_service.get_document_download(db, profile, doc_id)
    return FileResponse(
        path=str(path),
        filename=row.file_name,
        media_type=row.mime_type or "application/octet-stream",
        content_disposition_type="attachment",
    )


