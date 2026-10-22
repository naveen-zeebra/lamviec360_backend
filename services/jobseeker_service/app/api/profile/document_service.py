from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
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
from shared.utils.document_encryption import (
    encrypt_document_data,
    decrypt_document_data,
    hash_archive_pin,
    verify_archive_pin,
)

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
        "is_encrypted": bool(getattr(row, "is_encrypted", True)),
        "is_password_protected": bool(getattr(row, "is_password_protected", False)),
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
    profile = db.query(JobSeekerProfile).filter(JobSeekerProfile.id == profile_id).first()

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
        "has_archive_pin": bool(profile and profile.archive_pin_hash),
        "is_archive_locked": bool(profile and profile.is_archive_locked),
        "encryption_standard": "AES-256",
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
        "has_archive_pin": bool(profile.archive_pin_hash),
        "is_archive_locked": bool(profile.is_archive_locked),
        "encryption_standard": "AES-256",
    }


def save_doc_bytes(profile_id: int, original_name: str, data: bytes, user_pin: Optional[str] = None) -> tuple[str, str, int, str]:
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

    # JSP-FR-012: Encrypt data before writing to physical disk
    encrypted_data = encrypt_document_data(data, user_pin=user_pin)

    safe = safe_filename(original_name)
    unique = f"{uuid.uuid4().hex[:12]}_{safe}"
    target_dir = get_uploads_root() / "documents" / str(profile_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / unique

    with open(target_path, "wb") as f:
        f.write(encrypted_data)

    mime = "application/pdf" if ext == "pdf" else ("image/jpeg" if ext in ("jpg", "jpeg") else ("image/png" if ext == "png" else "application/octet-stream"))
    file_url = f"/uploads/documents/{profile_id}/{unique}"
    return file_url, safe, size_bytes, mime


def add_document(
    db: Session,
    profile: JobSeekerProfile,
    upload: UploadFile,
    category: str = "other",
    title: Optional[str] = None,
    protect_with_pin: bool = False,
    pin: Optional[str] = None,
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

    # Encrypt with PIN if user requested or profile has active PIN
    effective_pin = pin if pin else None
    file_url, file_name, size_bytes, mime = save_doc_bytes(profile.id, upload.filename, data, user_pin=effective_pin)
    doc_title = (title or "").strip() or Path(file_name).stem.replace("_", " ").title()

    is_protected = bool(protect_with_pin or profile.archive_pin_hash)

    row = JobSeekerDocument(
        jobseeker_id=profile.id,
        category=cat_clean,
        title=doc_title,
        file_name=file_name,
        file_url=file_url,
        mime_type=mime,
        size_bytes=size_bytes,
        is_encrypted=True,
        is_password_protected=is_protected,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    logger.info(f"Added encrypted document id={row.id} for profile_id={profile.id} ({doc_title})")
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

    # Safely remove physical encrypted file from disk
    try:
        rel = file_url.lstrip("/")
        if rel.startswith("uploads/"):
            rel = rel[len("uploads/"):]
        target = get_uploads_root() / rel
        if target.exists():
            target.unlink()
    except Exception as e:
        logger.warning(f"Could not remove physical document file: {e}")


def get_document_download(db: Session, profile: JobSeekerProfile, doc_id: int, pin: Optional[str] = None):
    """
    Retrieves document target path and row, checking PIN authorization if protected.
    Returns (target_path, row).
    """
    row = db.query(JobSeekerDocument).filter(
        JobSeekerDocument.id == doc_id,
        JobSeekerDocument.jobseeker_id == profile.id,
    ).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    # Check if access requires PIN verification
    if profile.archive_pin_hash:
        if pin:
            if not verify_archive_pin(pin, profile.archive_pin_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Security PIN.",
                )
        elif getattr(profile, "is_archive_locked", False):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Security PIN required to access this document.",
            )

    rel = row.file_url.lstrip("/")
    if rel.startswith("uploads/"):
        rel = rel[len("uploads/"):]
    target = get_uploads_root() / rel
    if not target.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File is not available on disk.")

    return target, row


def get_document_decrypted_content(db: Session, profile: JobSeekerProfile, doc_id: int, pin: Optional[str] = None) -> Tuple[bytes, JobSeekerDocument]:
    """
    Retrieves document and decrypts its binary content on-the-fly.
    """
    target, row = get_document_download(db, profile, doc_id, pin=pin)
    raw_bytes = target.read_bytes()
    decrypted = decrypt_document_data(raw_bytes, user_pin=pin)
    return decrypted, row


# ---- Archive Security PIN Management (JSP-FR-012) ---------------------------

def set_archive_pin(db: Session, profile: JobSeekerProfile, new_pin: str, current_pin: Optional[str] = None) -> bool:
    """Sets or updates candidate's document archive protection PIN."""
    clean_pin = (new_pin or "").strip()
    if len(clean_pin) < 4:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PIN must be at least 4 characters.")

    if profile.archive_pin_hash:
        if not current_pin or not verify_archive_pin(current_pin, profile.archive_pin_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current PIN is incorrect.")

    profile.archive_pin_hash = hash_archive_pin(clean_pin)
    profile.is_archive_locked = True
    db.commit()
    db.refresh(profile)
    logger.info(f"Updated archive PIN for profile_id={profile.id}")
    return True


def verify_archive_pin_service(db: Session, profile: JobSeekerProfile, pin: str) -> bool:
    """Validates PIN and temporarily unlocks the candidate's archive."""
    if not profile.archive_pin_hash:
        return True
    if not pin or not verify_archive_pin(pin, profile.archive_pin_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid PIN. Please try again.")

    profile.is_archive_locked = False
    db.commit()
    db.refresh(profile)
    return True


def lock_archive(db: Session, profile: JobSeekerProfile) -> bool:
    """Locks the candidate's archive."""
    profile.is_archive_locked = True
    db.commit()
    db.refresh(profile)
    return True


def remove_archive_pin(db: Session, profile: JobSeekerProfile, current_pin: str) -> bool:
    """Removes archive PIN protection."""
    if not profile.archive_pin_hash:
        return True
    if not current_pin or not verify_archive_pin(current_pin, profile.archive_pin_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current PIN is incorrect.")

    profile.archive_pin_hash = None
    profile.is_archive_locked = False
    db.commit()
    db.refresh(profile)
    logger.info(f"Removed archive PIN for profile_id={profile.id}")
    return True
