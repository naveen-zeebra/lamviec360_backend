import re
import uuid
from pathlib import Path
from typing import Optional, Tuple

from fastapi import HTTPException, status

from shared.environment import ROOT_DIR, env

MAX_RESUMES_PER_SEEKER = 5
MAX_RESUME_BYTES = 5 * 1024 * 1024
ALLOWED_RESUME_EXT = {".pdf", ".doc", ".docx"}
MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_RESUME_ERROR = "You can save a maximum of 5 résumés. Remove one before uploading another."


def get_uploads_root() -> Path:
    raw = Path(str(env.UPLOAD_DIR or "./uploads"))
    if raw.is_absolute():
        root = raw
    else:
        normalized = str(raw).replace("\\", "/").lstrip("./")
        root = ROOT_DIR / (normalized or "uploads")
    root.mkdir(parents=True, exist_ok=True)
    return root


def validate_resume_filename(filename: str) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_RESUME_EXT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Allowed formats: PDF, DOC, and DOCX only",
        )
    return ext


def validate_resume_size(size: int) -> None:
    if size is None or size <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume file is empty.",
        )
    if size > MAX_RESUME_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume file size must not exceed 5 MB",
        )


def safe_filename(name: str) -> str:
    base = Path(name or "resume.pdf").name
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", base).strip("._") or "resume.pdf"
    return cleaned[:180]


def read_upload_bytes(upload) -> bytes:
    if upload is None:
        return b""
    if hasattr(upload, "file") and upload.file is not None:
        try:
            upload.file.seek(0)
        except Exception:
            pass
        data = upload.file.read()
        return data or b""
    read = getattr(upload, "read", None)
    if callable(read):
        data = read()
        return data or b""
    return b""


def save_resume_bytes(jobseeker_id: int, original_name: str, data: bytes, subdir: str = "") -> Tuple[str, str, int, str]:
    ext = validate_resume_filename(original_name)
    validate_resume_size(len(data or b""))
    rel_dir = Path("resumes") / str(jobseeker_id)
    if subdir:
        rel_dir = rel_dir / subdir
    dest_dir = get_uploads_root() / rel_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid.uuid4().hex}_{safe_filename(original_name)}"
    dest = dest_dir / stored
    dest.write_bytes(data)
    public_url = f"/uploads/{rel_dir.as_posix()}/{stored}"
    mime = MIME_BY_EXT.get(ext, "application/octet-stream")
    return public_url, Path(original_name).name, len(data), mime


def absolute_path_from_url(file_url: str) -> Optional[Path]:
    if not file_url:
        return None
    prefix = "/uploads/"
    if file_url.startswith(prefix):
        return get_uploads_root() / file_url[len(prefix):]
    return None


def delete_resume_file(file_url: str) -> None:
    path = absolute_path_from_url(file_url)
    if path and path.exists() and path.is_file():
        try:
            path.unlink()
        except OSError:
            pass
