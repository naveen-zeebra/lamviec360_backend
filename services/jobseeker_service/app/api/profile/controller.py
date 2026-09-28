# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/profile/controller.py
# Purpose : Orchestration layer for Job Seeker Profile & Saved Jobs
# ─────────────────────────────────────────────────────────────────────────────

from typing import Dict, Any, List
from fastapi import HTTPException
from sqlalchemy.orm import Session

from shared.models import User
from shared.utils.logger import get_logger

from . import service
from .schemas import JobSeekerProfileUpdateSchema

logger = get_logger("jobseeker_profile_controller")


def get_profile_controller(user: User, db: Session) -> Dict[str, Any]:
    """Retrieve full jobseeker profile."""
    profile = service.get_or_create_jobseeker_profile(db, user)
    return service.serialize_profile(user, profile)


def update_profile_controller(
    data: JobSeekerProfileUpdateSchema,
    user: User,
    db: Session,
) -> Dict[str, Any]:
    """Update profile and user attributes."""
    profile = service.get_or_create_jobseeker_profile(db, user)
    data_dict = data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else data.dict(exclude_unset=True)
    user, profile = service.update_profile_and_user(db, user, profile, data_dict)
    return service.serialize_profile(user, profile)


def get_saved_jobs_controller(user: User, db: Session) -> List[Dict[str, Any]]:
    """Retrieve saved jobs list."""
    profile = service.get_or_create_jobseeker_profile(db, user)
    return service.get_saved_jobs_for_profile(db, profile.id)


def save_job_controller(job_id: int, user: User, db: Session) -> None:
    """Save a job posting."""
    profile = service.get_or_create_jobseeker_profile(db, user)
    success = service.save_job_for_profile(db, profile.id, job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")


def unsave_job_controller(job_id: int, user: User, db: Session) -> None:
    """Unsave a job posting."""
    profile = service.get_or_create_jobseeker_profile(db, user)
    service.unsave_job_for_profile(db, profile.id, job_id)
