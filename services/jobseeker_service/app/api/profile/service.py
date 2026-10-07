# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/profile/service.py
# Purpose : Domain & persistence logic for Job Seeker Profile & Saved Jobs
# ─────────────────────────────────────────────────────────────────────────────

from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status

from shared.models import User, JobSeekerProfile, SavedJob, JobPosting
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("jobseeker_profile_service")


def compute_profile_completeness(user: User, profile: JobSeekerProfile) -> int:
    """
    BR-101-02: Profile Completeness.
    Computes profile completeness percentage (0-100%) across 10 core candidate dimensions.
    Requires at least 60% completeness to submit job applications.
    """
    if not user or not profile:
        return 0

    checks = [
        bool(user.full_name and len(user.full_name.strip()) >= 2),
        bool(user.phone and len(user.phone.strip()) >= 5),
        bool(user.email and len(user.email.strip()) > 0),
        bool(profile.headline and len(profile.headline.strip()) > 0),
        bool(profile.city and len(profile.city.strip()) > 0),
        bool(profile.skills and len(str(profile.skills).strip()) > 0),
        bool(profile.resume_url and len(profile.resume_url.strip()) > 0),
        bool(profile.bio and len(profile.bio.strip()) > 0),
        bool(
            (profile.experience_years is not None and float(profile.experience_years) > 0)
            or (profile.expected_salary is not None and float(profile.expected_salary) > 0)
        ),
        bool(user.avatar_url or profile.linkedin_url or profile.github_url),
    ]

    completed_count = sum(1 for c in checks if c)
    return int((completed_count / len(checks)) * 100)


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
    completeness = compute_profile_completeness(user, profile)
    has_verified_contact = bool((user.email and user.is_verified) or (user.phone and user.is_verified))

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
        # BR-101-07: Profile Visibility
        "is_visible": getattr(profile, "is_visible", True),
        "visibility": getattr(profile, "visibility", "public"),
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
    # BR-101-01 & BR-101-06: Check unique phone if updated
    if data.get("phone") is not None:
        new_phone = str(data["phone"]).strip()
        if new_phone:
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
                    detail="An active account with this phone number already exists (BR-101-01, BR-101-06).",
                )
        user.phone = new_phone or None

    if data.get("full_name") is not None:
        user.full_name = data["full_name"]
    if data.get("avatar_url") is not None:
        user.avatar_url = data["avatar_url"]

    # BR-101-05: Expected salary validation (1M - 500M VND)
    if "expected_salary" in data and data["expected_salary"] is not None:
        salary_val = float(data["expected_salary"])
        if salary_val < 1_000_000 or salary_val > 500_000_000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Salary expectation must be within the range of 1M–500M VND per month (1,000,000 to 500,000,000 VND) (BR-101-05).",
            )
        profile.expected_salary = salary_val

    # BR-101-07: Profile Visibility (takes effect immediately)
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
