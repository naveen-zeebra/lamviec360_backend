from pathlib import Path
from typing import Any, Dict, List, Optional
import os
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import func

from shared.models import JobSeekerProfile, JobSeekerDocument
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger
from shared.utils.resume_storage import get_uploads_root, safe_filename

logger = get_logger("jobseeker_document_service")

from shared.config.upload_config import UPLOAD_CONFIG

# JSP-FR-012 Constraints:
# Re-exported for backward compatibility
MAX_DOC_BYTES = UPLOAD_CONFIG.document_archive.max_size_bytes
MAX_STORAGE_QUOTA_BYTES = UPLOAD_CONFIG.document_archive.quota_bytes
ALLOWED_DOC_EXT = UPLOAD_CONFIG.document_archive.allowed_extensions_list
ALLOWED_CATEGORIES = UPLOAD_CONFIG.document_archive.allowed_categories


def serialize_document(row: JobSeekerDocument) -> Dict[str, Any]:
    cat = row.category
    if cat == "relieving_letter":
        cat = "relieving"
    return {
        "id": row.id,
        "category": cat,
        "title": row.title,
        "file_name": row.file_name,
        "file_url": row.file_url,
        "mime_type": row.mime_type,
        "size_bytes": int(row.size_bytes or 0),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def get_archive_usage(db: Session, profile_id: int) -> Dict[str, Any]:
    """Calculate total storage used by candidate across all archived documents."""
    total_bytes = (
        db.query(func.coalesce(func.sum(JobSeekerDocument.size_bytes), 0))
        .filter(JobSeekerDocument.jobseeker_id == profile_id)
        .scalar()
    ) or 0

    doc_count = db.query(JobSeekerDocument).filter(JobSeekerDocument.jobseeker_id == profile_id).count()

    used_mb = round(total_bytes / (1024 * 1024), 2)
    quota_mb = round(MAX_STORAGE_QUOTA_BYTES / (1024 * 1024), 0)
    percent_used = min(100, round((total_bytes / MAX_STORAGE_QUOTA_BYTES) * 100, 1))

    return {
        "used_bytes": int(total_bytes),
        "used_mb": used_mb,
        "quota_bytes": MAX_STORAGE_QUOTA_BYTES,
        "quota_mb": quota_mb,
        "percent_used": percent_used,
        "count": doc_count,
    }


def list_documents(db: Session, profile: JobSeekerProfile, category: Optional[str] = None) -> Dict[str, Any]:
    query = db.query(JobSeekerDocument).filter(JobSeekerDocument.jobseeker_id == profile.id)
    if category and category.lower() != "all":
        cat_filter = category.lower()
        if cat_filter in ("relieving", "relieving_letter"):
            query = query.filter(JobSeekerDocument.category.in_(["relieving", "relieving_letter"]))
        else:
            query = query.filter(JobSeekerDocument.category == cat_filter)
    rows = query.order_by(JobSeekerDocument.created_at.desc()).all()

    usage = get_archive_usage(db, profile.id)
    return {
        "items": [serialize_document(r) for r in rows],
        "usage": usage,
    }


def save_doc_bytes(profile_id: int, original_name: str, data: bytes) -> tuple[str, str, int, str]:
    ext = (Path(original_name).suffix or "").lstrip(".").lower()
    if ext not in ALLOWED_DOC_EXT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format. Allowed formats: {', '.join(ALLOWED_DOC_EXT).upper()}",
        )
    size_bytes = len(data)
    if size_bytes > MAX_DOC_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=UPLOAD_CONFIG.document_archive.max_size_error_message,
        )

    safe = safe_filename(original_name)
    unique = f"{uuid.uuid4().hex[:12]}_{safe}"
    target_dir = get_uploads_root() / "documents" / str(profile_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / unique

    with open(target_path, "wb") as f:
        f.write(data)

    mime = "application/pdf" if ext == "pdf" else ("image/jpeg" if ext in ("jpg", "jpeg") else ("image/png" if ext == "png" else "application/octet-stream"))
    file_url = f"/uploads/documents/{profile_id}/{unique}"
    return file_url, safe, size_bytes, mime


def add_document(
    db: Session,
    profile: JobSeekerProfile,
    upload: UploadFile,
    category: str = "other",
    title: Optional[str] = None,
) -> JobSeekerDocument:
    if not upload or not getattr(upload, "filename", None):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document file is required.")

    # Validate and normalize category
    cat_clean = (category or "other").strip().lower()
    if cat_clean == "relieving_letter":
        cat_clean = "relieving"
    if cat_clean not in ALLOWED_CATEGORIES:
        cat_clean = "other"

    data = upload.file.read()
    file_size = len(data)

    # Check user storage quota
    usage = get_archive_usage(db, profile.id)
    if usage["used_bytes"] + file_size > MAX_STORAGE_QUOTA_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=UPLOAD_CONFIG.document_archive.quota_error_message,
        )

    file_url, file_name, size_bytes, mime = save_doc_bytes(profile.id, upload.filename, data)
    doc_title = (title or "").strip() or Path(file_name).stem.replace("_", " ").title()

    row = JobSeekerDocument(
        jobseeker_id=profile.id,
        category=cat_clean,
        title=doc_title,
        file_name=file_name,
        file_url=file_url,
        mime_type=mime,
        size_bytes=size_bytes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    logger.info(f"Added document id={row.id} for profile_id={profile.id} ({doc_title})")
    return row


def delete_document(db: Session, profile: JobSeekerProfile, doc_id: int) -> None:
    row = db.query(JobSeekerDocument).filter(
        JobSeekerDocument.id == doc_id,
        JobSeekerDocument.jobseeker_id == profile.id,
    ).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    file_url = row.file_url
    db.delete(row)
    db.commit()

    # Safely remove file from disk
    try:
        rel = file_url.lstrip("/")
        if rel.startswith("uploads/"):
            rel = rel[len("uploads/"):]
        target = get_uploads_root() / rel
        if target.exists():
            target.unlink()
    except Exception as e:
        logger.warning(f"Could not remove physical document file: {e}")


def get_document_download(db: Session, profile: JobSeekerProfile, doc_id: int):
    row = db.query(JobSeekerDocument).filter(
        JobSeekerDocument.id == doc_id,
        JobSeekerDocument.jobseeker_id == profile.id,
    ).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    rel = row.file_url.lstrip("/")
    if rel.startswith("uploads/"):
        rel = rel[len("uploads/"):]
    target = get_uploads_root() / rel
    if not target.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File is not available on disk.")

    return target, row

