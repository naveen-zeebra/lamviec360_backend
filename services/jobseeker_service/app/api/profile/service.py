# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/profile/service.py
# Purpose : Domain & persistence logic for Job Seeker Profile & Saved Jobs
# ─────────────────────────────────────────────────────────────────────────────

import base64
import uuid
from pathlib import Path
from urllib.parse import unquote
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session

from shared.environment import env
from shared.models import User, JobSeekerProfile, SavedJob, JobPosting
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger
from shared.config.upload_config import UPLOAD_CONFIG

logger = get_logger("jobseeker_profile_service")


def persist_avatar_data(user: User, avatar_data: Optional[str]) -> Optional[str]:
    """
    Decodes and writes data-URL avatars to disk as clean image files in uploads/avatars/,
    returning the static URL path '/uploads/avatars/...'.
    Normal URLs or paths are preserved as-is.
    """
    if not avatar_data:
        return avatar_data

    raw = str(avatar_data).strip()
    if raw.startswith("data:image/"):
        header, sep, data_part = raw.partition(",")
        if sep:
            header_lower = header.lower()
            ext = "png"
            if "jpeg" in header_lower or "jpg" in header_lower:
                ext = "jpg"
            elif "webp" in header_lower:
                ext = "webp"
            elif "gif" in header_lower:
                ext = "gif"
            elif "svg" in header_lower:
                ext = "svg"

            upload_root = Path(str(env.UPLOAD_DIR or "./uploads")).resolve()
            avatar_dir = upload_root / "avatars"
            avatar_dir.mkdir(parents=True, exist_ok=True)

            filename = f"avatar_{user.id}_{uuid.uuid4().hex[:8]}.{ext}"
            target_path = avatar_dir / filename

            if ";base64" in header_lower:
                try:
                    payload_bytes = base64.b64decode(data_part)
                    if len(payload_bytes) > UPLOAD_CONFIG.avatar.max_size_bytes:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=UPLOAD_CONFIG.avatar.max_size_error_message,
                        )
                    target_path.write_bytes(payload_bytes)
                    return f"/uploads/avatars/{filename}"
                except HTTPException:
                    raise
                except Exception as e:
                    logger.warning(f"Failed to decode base64 avatar: {e}")
            elif "svg" in header_lower:
                try:
                    svg_content = unquote(data_part)
                    target_path.write_text(svg_content, encoding="utf-8")
                    return f"/uploads/avatars/{filename}"
                except Exception as e:
                    logger.warning(f"Failed to save svg avatar: {e}")

    return raw


def save_avatar_file(db: Session, user: User, file: UploadFile) -> str:
    """Save an uploaded image file for user avatar and persist path."""
    content_type = (file.content_type or "").lower()
    allowed_exts = UPLOAD_CONFIG.avatar.allowed_extensions
    allowed_types = UPLOAD_CONFIG.avatar.allowed_mime_types

    ext = Path(file.filename or "").suffix.lower()
    if ext not in allowed_exts or (content_type and content_type not in allowed_types):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=UPLOAD_CONFIG.avatar.format_error_message,
        )

    file_ext = ext.lstrip(".") if ext else ("jpg" if "jpeg" in content_type else "png")

    upload_root = Path(str(env.UPLOAD_DIR or "./uploads")).resolve()
    avatar_dir = upload_root / "avatars"
    avatar_dir.mkdir(parents=True, exist_ok=True)

    content = file.file.read()
    if len(content) > UPLOAD_CONFIG.avatar.max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=UPLOAD_CONFIG.avatar.max_size_error_message,
        )

    filename = f"avatar_{user.id}_{uuid.uuid4().hex[:8]}.{file_ext}"
    target_path = avatar_dir / filename
    target_path.write_bytes(content)

    user.avatar_url = f"/uploads/avatars/{filename}"
    db.commit()
    db.refresh(user)
    logger.info(f"Updated avatar for user_id={user.id} -> {user.avatar_url}")
    return user.avatar_url


def get_profile_completeness_details(user: User, profile: JobSeekerProfile) -> Dict[str, Any]:
    """
    JSP-FR-005a / BR-101-02: Profile Completeness.
    Calculation: (filled required fields / total required fields) * 100%
    Required fields: Name, Email, Phone, Location, Work Experience (>=1), Education (>=1), Skills (>=3), Resume (>=1)
    """
    if not user or not profile:
        return {"completeness": 0, "missing_fields": ["All fields"], "can_apply": False}

    # Helper to parse skills count
    skills_raw = str(profile.skills or "").strip()
    skills_count = 0
    if skills_raw:
        if skills_raw.startswith("["):
            import json
            try:
                skills_list = json.loads(skills_raw)
                skills_count = len(skills_list) if isinstance(skills_list, list) else 1
            except Exception:
                skills_count = len([s for s in skills_raw.split(",") if s.strip()])
        else:
            skills_count = len([s for s in skills_raw.split(",") if s.strip()])

    has_resume = bool(
        (profile.resume_url and len(profile.resume_url.strip()) > 0)
        or bool(getattr(profile, "resumes", None) and len(profile.resumes) > 0)
    )

    requirements = [
        ("Full Name", bool(user.full_name and len(user.full_name.strip()) >= 2)),
        ("Email Address", bool(user.email and len(user.email.strip()) > 0)),
        ("Phone Number", bool(user.phone and len(user.phone.strip()) >= 5)),
        ("Location / City", bool((profile.city and len(profile.city.strip()) > 0) or (profile.country and len(profile.country.strip()) > 0))),
        ("Work Experience (>=1)", bool(profile.experience_years is not None and float(profile.experience_years) > 0)),
        ("Education (>=1)", bool((profile.headline and len(profile.headline.strip()) > 0) or (profile.bio and len(profile.bio.strip()) > 0))),
        ("Skills (>=3)", skills_count >= 3),
        ("Resume (>=1)", has_resume),
    ]

    completed = sum(1 for name, ok in requirements if ok)
    missing = [name for name, ok in requirements if not ok]
    percentage = int(round((completed / len(requirements)) * 100))

    return {
        "completeness": percentage,
        "missing_fields": missing,
        "can_apply": percentage >= 60,
        "min_required": 60,
    }


def compute_profile_completeness(user: User, profile: JobSeekerProfile) -> int:
    """Computes profile completeness percentage (0-100%) per JSP-FR-005a."""
    return get_profile_completeness_details(user, profile)["completeness"]


def auto_archive_inactive_profiles(db: Session) -> int:
    """
    BR-101-08: Inactive Profile.
    Profiles with no login activity for 12 months must be automatically archived.
    Archived profiles no longer appear as active profiles.
    Records archive date and reason.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=365)
    candidates = (
        db.query(JobSeekerProfile)
        .join(User, JobSeekerProfile.user_id == User.id)
        .filter(
            JobSeekerProfile.is_archived == False,
            (
                (User.last_login != None) & (User.last_login < cutoff)
                | (User.last_login == None) & (User.created_at < cutoff)
            ),
        )
        .all()
    )

    now = datetime.now(timezone.utc)
    archived_count = 0
    for p in candidates:
        p.is_archived = True
        p.archived_at = now
        p.archive_reason = "No login activity for 12 months (BR-101-08)"
        p.is_visible = False
        p.job_availability = "not_looking"
        archived_count += 1

    if archived_count > 0:
        db.commit()
        logger.info(f"Auto-archived {archived_count} inactive profiles per BR-101-08")
    return archived_count


@service_error_handler
def get_or_create_jobseeker_profile(db: Session, user: User) -> JobSeekerProfile:
    """Retrieve existing profile or create empty candidate profile."""
    # Check and trigger auto archiving check
    try:
        auto_archive_inactive_profiles(db)
    except Exception as e:
        logger.warning(f"Could not run auto_archive_inactive_profiles: {e}")

    profile = db.query(JobSeekerProfile).filter(JobSeekerProfile.user_id == user.id).first()
    if not profile:
        profile = JobSeekerProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        logger.info(f"Initialized jobseeker profile for user_id={user.id}")
    return profile


def serialize_profile(user: User, profile: JobSeekerProfile) -> Dict[str, Any]:
    """Serialize user and profile data with business rule fields."""
    from sqlalchemy.orm import object_session
    from .resume_service import ensure_legacy_resume, serialize_resume

    try:
        db = object_session(profile)
        if db:
            ensure_legacy_resume(db, profile)
            db.refresh(profile)
    except Exception:
        pass

    completeness = compute_profile_completeness(user, profile)
    has_verified_contact = bool((user.email and user.is_verified) or (user.phone and user.is_verified))
    resume_rows = list(getattr(profile, "resumes", None) or [])
    resume_rows.sort(key=lambda r: (not bool(r.is_default), r.id or 0))

    return {
        "id": profile.id,
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "avatar_url": user.avatar_url,
        "headline": profile.headline,
        "bio": profile.bio,
        "resume_url": profile.resume_url,
        "resumes": [serialize_resume(r) for r in resume_rows],
        "skills": profile.skills,
        "experience_years": float(profile.experience_years or 0),
        "expected_salary": float(profile.expected_salary) if profile.expected_salary else None,
        "city": profile.city,
        "country": profile.country,
        "github_url": profile.github_url,
        "linkedin_url": profile.linkedin_url,
        # BR-101-02: Completeness percentage
        "completeness": completeness,
        "can_apply": completeness >= 60,
        # BR-101-04: Verified contact method
        "is_verified": user.is_verified,
        "has_verified_contact": has_verified_contact,
        # BR-101-07: Profile Visibility (takes effect immediately)
        "is_visible": getattr(profile, "is_visible", True),
        "visibility": getattr(profile, "visibility", "public"),
        "job_availability": getattr(profile, "job_availability", "open_to_work") or "open_to_work",
        # BR-101-08: Inactive Archive
        "is_archived": getattr(profile, "is_archived", False),
        "archived_at": profile.archived_at.isoformat() if getattr(profile, "archived_at", None) else None,
        "archive_reason": getattr(profile, "archive_reason", None),
    }


@service_error_handler
def update_profile_and_user(
    db: Session,
    user: User,
    profile: JobSeekerProfile,
    data: Dict[str, Any],
) -> Tuple[User, JobSeekerProfile]:
    """Update User and JobSeekerProfile attributes, enforcing business rules."""
    # Check unique phone only if updated to a different phone number
    if data.get("phone") is not None:
        new_phone = str(data["phone"]).strip()
        current_phone = (user.phone or "").strip()
        if new_phone and new_phone != current_phone:
            existing_phone = (
                db.query(User)
                .filter(
                    User.phone == new_phone,
                    User.id != user.id,
                    User.is_active == True,
                    User.is_deleted == False,
                )
                .first()
            )
            if existing_phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="An active account with this phone number already exists.",
                )
            user.phone = new_phone
        elif not new_phone:
            user.phone = None

    if data.get("full_name") is not None:
        user.full_name = data["full_name"]
    if data.get("avatar_url") is not None:
        user.avatar_url = persist_avatar_data(user, data["avatar_url"])

    # Expected salary validation (1M - 500M VND)
    if "expected_salary" in data and data["expected_salary"] is not None:
        salary_val = float(data["expected_salary"])
        if salary_val < 1_000_000 or salary_val > 500_000_000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Salary expectation must be within the range of 1M–500M VND per month (1,000,000 to 500,000,000 VND).",
            )
        profile.expected_salary = salary_val

    # BR-101-07 & BR-101-08: Profile Visibility & Job Availability (takes effect immediately)
    if "job_availability" in data and data["job_availability"] is not None:
        av_val = str(data["job_availability"]).strip().lower()
        if av_val in ["open_to_work", "open_to_opportunities", "not_looking"]:
            profile.job_availability = av_val
            # If candidate sets themselves to not_looking and didn't specify visibility, default to private
            if av_val == "not_looking" and "is_visible" not in data and "visibility" not in data:
                profile.is_visible = False
                profile.visibility = "private"
            elif av_val in ["open_to_work", "open_to_opportunities"] and "is_visible" not in data and "visibility" not in data:
                profile.is_visible = True
                profile.visibility = "public"

    if "is_visible" in data and data["is_visible"] is not None:
        profile.is_visible = bool(data["is_visible"])
        profile.visibility = "public" if profile.is_visible else "private"
    if "visibility" in data and data["visibility"] is not None:
        profile.visibility = str(data["visibility"])
        profile.is_visible = profile.visibility.lower() in ["public", "public to employers"]

    profile_fields = [
        "headline", "bio", "resume_url", "skills",
        "experience_years", "city",
        "country", "github_url", "linkedin_url"
    ]
    for field in profile_fields:
        if field in data and data[field] is not None:
            setattr(profile, field, data[field])

    db.commit()
    db.refresh(profile)
    db.refresh(user)
    logger.info(f"Updated profile for user_id={user.id} (visibility={profile.visibility}, completeness={compute_profile_completeness(user, profile)}%)")
    return user, profile


@service_error_handler
def get_saved_jobs_for_profile(db: Session, profile_id: int) -> List[Dict[str, Any]]:
    """Retrieve saved jobs list."""
    saved = db.query(SavedJob).filter(SavedJob.jobseeker_id == profile_id).all()
    results = []
    for s in saved:
        if s.job and not s.job.is_deleted:
            results.append({
                "saved_id": s.id,
                "saved_at": s.created_at.isoformat() if s.created_at else None,
                "job": {
                    "id": s.job.id,
                    "title": s.job.title,
                    "job_type": s.job.job_type,
                    "city": s.job.city,
                    "country": s.job.country,
                    "location": f"{s.job.city}, {s.job.country}" if s.job.city and s.job.country else (s.job.city or s.job.country or "Remote"),
                    "salary_min": float(s.job.salary_min) if s.job.salary_min else None,
                    "salary_max": float(s.job.salary_max) if s.job.salary_max else None,
                    "salary_currency": getattr(s.job, "salary_currency", "VND") or "VND",
                    "workplace_type": getattr(s.job, "workplace_type", "On-site") or "On-site",
                    "company_name": s.job.company.company_name if s.job.company else "Unknown",
                    "company_logo": s.job.company.logo_url if s.job.company else None,
                }
            })
    return results


@service_error_handler
def save_job_for_profile(db: Session, profile_id: int, job_id: int) -> bool:
    """Save a job posting to bookmark list. Returns False if already saved."""
    job = db.query(JobPosting).filter(JobPosting.id == job_id, JobPosting.is_deleted == False).first()
    if not job:
        return False

    existing = db.query(SavedJob).filter(
        SavedJob.jobseeker_id == profile_id,
        SavedJob.job_id == job_id,
    ).first()
    if existing:
        return True

    # BR-015 / BR-201-05: Maximum 100 saved jobs per candidate
    current_count = db.query(SavedJob).filter(SavedJob.jobseeker_id == profile_id).count()
    if current_count >= 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can save up to 100 jobs simultaneously (BR-201-05). Please remove a saved job before adding another.",
        )

    new_saved = SavedJob(jobseeker_id=profile_id, job_id=job_id)
    db.add(new_saved)
    db.commit()
    logger.info(f"Saved job id={job_id} for profile_id={profile_id}")
    return True



@service_error_handler
def unsave_job_for_profile(db: Session, profile_id: int, job_id: int) -> None:
    """Remove a job from saved bookmarks."""
    db.query(SavedJob).filter(
        SavedJob.jobseeker_id == profile_id,
        SavedJob.job_id == job_id,
    ).delete()
    db.commit()
    logger.info(f"Unsaved job id={job_id} for profile_id={profile_id}")
