# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/profile/router.py
# Purpose : Presentation layer (FastAPI endpoints) for Job Seeker Profile
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional
from fastapi import APIRouter, Depends, File, Form, Header, Request, UploadFile, Body, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import User
from shared.schemas import APIResponse
from shared.utils import get_current_jobseeker, success_response
from shared.utils.document_encryption import decrypt_document_data

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
    protect_with_pin: Optional[bool] = Form(False),
    pin: Optional[str] = Form(None),
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    resolved_category = (category or request.query_params.get("category") or "other").strip().lower()
    resolved_title = title if title is not None else (request.query_params.get("title") or "")
    resolved_protect = bool(protect_with_pin or request.query_params.get("protect_with_pin", "false").lower() in ("true", "1"))
    resolved_pin = pin or request.query_params.get("pin")

    profile = profile_service.get_or_create_jobseeker_profile(db, user)
    row = document_service.add_document(
        db,
        profile,
        file,
        category=resolved_category,
        title=resolved_title,
        protect_with_pin=resolved_protect,
        pin=resolved_pin,
    )
    usage = document_service.get_archive_usage(db, profile.id)
    return success_response(
        data={"item": document_service.serialize_document(row), "usage": usage},
        message="Document encrypted and uploaded to archive successfully.",
    )


@router.post("/documents/archive-pin", response_model=APIResponse[dict], summary="Set or update archive security PIN")
def set_candidate_archive_pin(
    payload: dict = Body(...),
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    profile = profile_service.get_or_create_jobseeker_profile(db, user)
    pin = payload.get("pin", "")
    current_pin = payload.get("current_pin")
    document_service.set_archive_pin(db, profile, pin, current_pin=current_pin)
    return success_response(
        data={"has_archive_pin": True, "is_archive_locked": True},
        message="Archive security PIN updated successfully.",
    )


@router.post("/documents/verify-pin", response_model=APIResponse[dict], summary="Verify archive security PIN to unlock")
def verify_candidate_archive_pin(
    payload: dict = Body(...),
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    profile = profile_service.get_or_create_jobseeker_profile(db, user)
    pin = payload.get("pin", "")
    document_service.verify_archive_pin_service(db, profile, pin)
    return success_response(
        data={"has_archive_pin": True, "is_archive_locked": False},
        message="Archive unlocked successfully.",
    )


@router.post("/documents/lock", response_model=APIResponse[dict], summary="Lock archive")
def lock_candidate_archive(
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    profile = profile_service.get_or_create_jobseeker_profile(db, user)
    document_service.lock_archive(db, profile)
    return success_response(
        data={"has_archive_pin": bool(profile.archive_pin_hash), "is_archive_locked": True},
        message="Archive locked.",
    )


@router.delete("/documents/archive-pin", response_model=APIResponse[dict], summary="Remove archive security PIN")
def remove_candidate_archive_pin(
    payload: dict = Body(...),
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    profile = profile_service.get_or_create_jobseeker_profile(db, user)
    current_pin = payload.get("current_pin", "")
    document_service.remove_archive_pin(db, profile, current_pin)
    return success_response(
        data={"has_archive_pin": False, "is_archive_locked": False},
        message="Archive PIN removed successfully.",
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
    pin: Optional[str] = None,
    x_archive_pin: Optional[str] = Header(None, alias="X-Archive-PIN"),
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    profile = profile_service.get_or_create_jobseeker_profile(db, user)
    provided_pin = pin or x_archive_pin
    path_or_content, row = document_service.get_document_download(db, profile, doc_id, pin=provided_pin)

    if isinstance(path_or_content, (bytes, bytearray)):
        content = bytes(path_or_content)
    elif hasattr(path_or_content, "read_bytes"):
        raw_bytes = path_or_content.read_bytes()
        content = decrypt_document_data(raw_bytes, user_pin=provided_pin)
    elif isinstance(path_or_content, str):
        with open(path_or_content, "rb") as f:
            content = decrypt_document_data(f.read(), user_pin=provided_pin)
    else:
        content = b""

    return Response(
        content=content,
        media_type=row.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{row.file_name}"'},
    )


