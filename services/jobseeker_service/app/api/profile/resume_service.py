from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from shared.models import JobSeekerProfile, JobSeekerResume
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger
from shared.utils.resume_storage import (
    MAX_RESUMES_PER_SEEKER,
    MAX_RESUME_ERROR,
    absolute_path_from_url,
    delete_resume_file,
    read_upload_bytes,
    save_resume_bytes,
)

logger = get_logger("jobseeker_resume_service")


def serialize_resume(row: JobSeekerResume) -> Dict[str, Any]:
    return {
        "id": row.id,
        "file_name": row.file_name,
        "file_url": row.file_url,
        "mime_type": row.mime_type,
        "size_bytes": int(row.size_bytes or 0),
        "is_default": bool(row.is_default),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _list_rows(db: Session, profile_id: int) -> List[JobSeekerResume]:
    return (
        db.query(JobSeekerResume)
        .filter(JobSeekerResume.jobseeker_id == profile_id)
        .order_by(JobSeekerResume.is_default.desc(), JobSeekerResume.created_at.asc())
        .all()
    )


@service_error_handler
def ensure_legacy_resume(db: Session, profile: JobSeekerProfile) -> None:
    """If profile.resume_url exists but the library is empty, seed one default row."""
    rows = _list_rows(db, profile.id)
    if rows:
        return
    if not (profile.resume_url and str(profile.resume_url).strip()):
        return
    url = profile.resume_url.strip()
    name = Path(url).name or "resume.pdf"
    row = JobSeekerResume(
        jobseeker_id=profile.id,
        file_name=name,
        file_url=url,
        mime_type="application/pdf",
        size_bytes=0,
        is_default=True,
    )
    db.add(row)
    db.commit()
    logger.info(f"Migrated legacy resume_url for profile_id={profile.id}")


def list_resumes_payload(db: Session, profile: JobSeekerProfile) -> Dict[str, Any]:
    ensure_legacy_resume(db, profile)
    items = [serialize_resume(r) for r in _list_rows(db, profile.id)]
    return {
        "items": items,
        "count": len(items),
        "max": MAX_RESUMES_PER_SEEKER,
    }


def get_default_resume(db: Session, profile: JobSeekerProfile) -> Optional[JobSeekerResume]:
    ensure_legacy_resume(db, profile)
    return (
        db.query(JobSeekerResume)
        .filter(JobSeekerResume.jobseeker_id == profile.id, JobSeekerResume.is_default == True)
        .first()
    ) or (
        db.query(JobSeekerResume)
        .filter(JobSeekerResume.jobseeker_id == profile.id)
        .order_by(JobSeekerResume.created_at.asc())
        .first()
    )


def get_owned_resume(db: Session, profile: JobSeekerProfile, resume_id: int) -> JobSeekerResume:
    row = (
        db.query(JobSeekerResume)
        .filter(JobSeekerResume.id == resume_id, JobSeekerResume.jobseeker_id == profile.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Résumé not found")
    return row


def _sync_profile_default(db: Session, profile: JobSeekerProfile) -> None:
    default = (
        db.query(JobSeekerResume)
        .filter(JobSeekerResume.jobseeker_id == profile.id, JobSeekerResume.is_default == True)
        .first()
    )
    if not default:
        default = (
            db.query(JobSeekerResume)
            .filter(JobSeekerResume.jobseeker_id == profile.id)
            .order_by(JobSeekerResume.created_at.asc())
            .first()
        )
        if default:
            default.is_default = True
    profile.resume_url = default.file_url if default else None


def add_resume_from_bytes(
    db: Session,
    profile: JobSeekerProfile,
    original_name: str,
    data: bytes,
    make_default: Optional[bool] = None,
) -> JobSeekerResume:
    count = db.query(JobSeekerResume).filter(JobSeekerResume.jobseeker_id == profile.id).count()
    if count >= MAX_RESUMES_PER_SEEKER:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MAX_RESUME_ERROR)

    file_url, file_name, size_bytes, mime = save_resume_bytes(profile.id, original_name, data)
    is_first = count == 0
    row = JobSeekerResume(
        jobseeker_id=profile.id,
        file_name=file_name,
        file_url=file_url,
        mime_type=mime,
        size_bytes=size_bytes,
        is_default=is_first if make_default is None else bool(make_default) or is_first,
    )
    if row.is_default:
        db.query(JobSeekerResume).filter(JobSeekerResume.jobseeker_id == profile.id).update({"is_default": False})
        row.is_default = True
    db.add(row)
    db.flush()
    _sync_profile_default(db, profile)
    db.commit()
    db.refresh(row)
    logger.info(f"Saved résumé id={row.id} for profile_id={profile.id} ({count + 1}/{MAX_RESUMES_PER_SEEKER})")
    return row


def add_resume_from_upload(db: Session, profile: JobSeekerProfile, upload) -> JobSeekerResume:
    if upload is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resume file is required")
    filename = getattr(upload, "filename", None) or "resume.pdf"
    data = read_upload_bytes(upload)
    return add_resume_from_bytes(db, profile, filename, data)


def set_default_resume(db: Session, profile: JobSeekerProfile, resume_id: int) -> JobSeekerResume:
    row = get_owned_resume(db, profile, resume_id)
    db.query(JobSeekerResume).filter(JobSeekerResume.jobseeker_id == profile.id).update({"is_default": False})
    row.is_default = True
    profile.resume_url = row.file_url
    db.commit()
    db.refresh(row)
    return row


def delete_resume(db: Session, profile: JobSeekerProfile, resume_id: int) -> None:
    row = get_owned_resume(db, profile, resume_id)
    file_url = row.file_url
    was_default = bool(row.is_default)
    db.delete(row)
    db.flush()
    remaining = _list_rows(db, profile.id)
    if was_default and remaining:
        remaining[0].is_default = True
    _sync_profile_default(db, profile)
    db.commit()
    delete_resume_file(file_url)


def download_path_for_resume(db: Session, profile: JobSeekerProfile, resume_id: int):
    row = get_owned_resume(db, profile, resume_id)
    path = absolute_path_from_url(row.file_url)
    if not path or not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Résumé file is not available for download")
    return path, row
