# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/profile/service.py
# Purpose : Domain & persistence logic for Job Seeker Profile & Saved Jobs
# ─────────────────────────────────────────────────────────────────────────────

from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from shared.models import User, JobSeekerProfile, SavedJob, JobPosting
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("jobseeker_profile_service")


@service_error_handler
def get_or_create_jobseeker_profile(db: Session, user: User) -> JobSeekerProfile:
    """Retrieve existing profile or create empty candidate profile."""
    profile = db.query(JobSeekerProfile).filter(JobSeekerProfile.user_id == user.id).first()
    if not profile:
        profile = JobSeekerProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        logger.info(f"Initialized jobseeker profile for user_id={user.id}")
    return profile


def serialize_profile(user: User, profile: JobSeekerProfile) -> Dict[str, Any]:
    """Serialize user and profile data."""
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
    }


@service_error_handler
def update_profile_and_user(
    db: Session,
    user: User,
    profile: JobSeekerProfile,
    data: Dict[str, Any],
) -> Tuple[User, JobSeekerProfile]:
    """Update User and JobSeekerProfile attributes."""
    if data.get("full_name") is not None:
        user.full_name = data["full_name"]
    if data.get("phone") is not None:
        user.phone = data["phone"]
    if data.get("avatar_url") is not None:
        user.avatar_url = data["avatar_url"]

    profile_fields = [
        "headline", "bio", "resume_url", "skills",
        "experience_years", "expected_salary", "city",
        "country", "github_url", "linkedin_url"
    ]
    for field in profile_fields:
        if field in data and data[field] is not None:
            setattr(profile, field, data[field])

    db.commit()
    db.refresh(profile)
    db.refresh(user)
    logger.info(f"Updated profile for user_id={user.id}")
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
