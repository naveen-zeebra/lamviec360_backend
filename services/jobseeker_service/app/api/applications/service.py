# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/applications/service.py
# Purpose : Domain & persistence logic for Candidate Job Applications
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from shared.models import User, JobSeekerProfile, JobPosting, JobApplication
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("jobseeker_applications_service")


@service_error_handler
def get_or_create_profile(db: Session, user: User) -> JobSeekerProfile:
    """Ensure candidate profile exists."""
    profile = db.query(JobSeekerProfile).filter(JobSeekerProfile.user_id == user.id).first()
    if not profile:
        profile = JobSeekerProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@service_error_handler
def get_active_job(db: Session, job_id: int) -> Optional[JobPosting]:
    """Retrieve active or published job for application."""
    return db.query(JobPosting).filter(
        JobPosting.id == job_id,
        JobPosting.status.in_(["active", "published"]),
        JobPosting.is_deleted == False,
    ).first()


@service_error_handler
def check_existing_application(db: Session, job_id: int, profile_id: int) -> bool:
    """Check if candidate already submitted an application for this vacancy."""
    existing = db.query(JobApplication).filter(
        JobApplication.job_id == job_id,
        JobApplication.jobseeker_id == profile_id,
    ).first()
    return existing is not None


@service_error_handler
def create_application(
    db: Session,
    job: JobPosting,
    profile: JobSeekerProfile,
    cover_letter: Optional[str] = None,
    resume_url: Optional[str] = None,
) -> JobApplication:
    """Create job application record and increment counter."""
    resolved_resume = resume_url or profile.resume_url

    application = JobApplication(
        job_id=job.id,
        jobseeker_id=profile.id,
        cover_letter=cover_letter,
        resume_url=resolved_resume,
        status="applied",
    )
    db.add(application)
    job.applications_count = (job.applications_count or 0) + 1
    db.commit()
    db.refresh(application)
    logger.info(f"Created application id={application.id} for job_id={job.id} by profile_id={profile.id}")
    return application


@service_error_handler
def list_my_applications(db: Session, profile_id: int) -> List[Dict[str, Any]]:
    """Retrieve all applications for the candidate profile."""
    records = (
        db.query(JobApplication)
        .filter(JobApplication.jobseeker_id == profile_id)
        .order_by(desc(JobApplication.created_at))
        .all()
    )

    results = []
    for app in records:
        results.append({
            "id": app.id,
            "status": app.status,
            "applied_at": app.created_at.isoformat() if app.created_at else None,
            "recruiter_notes": app.recruiter_notes,
            "job": {
                "id": app.job.id,
                "title": app.job.title,
                "job_type": app.job.job_type,
                "city": app.job.city,
                "company_name": app.job.company.company_name if app.job.company else "Unknown",
                "company_logo": app.job.company.logo_url if app.job.company else None,
            } if app.job else None,
        })
    return results


@service_error_handler
def get_application_by_id(db: Session, application_id: int, profile_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve detailed single application."""
    app = db.query(JobApplication).filter(
        JobApplication.id == application_id,
        JobApplication.jobseeker_id == profile_id,
    ).first()

    if not app:
        return None

    return {
        "id": app.id,
        "status": app.status,
        "cover_letter": app.cover_letter,
        "resume_url": app.resume_url,
        "recruiter_notes": app.recruiter_notes,
        "applied_at": app.created_at.isoformat() if app.created_at else None,
        "updated_at": app.updated_at.isoformat() if app.updated_at else None,
        "job": {
            "id": app.job.id,
            "title": app.job.title,
            "job_type": app.job.job_type,
            "city": app.job.city,
            "company_name": app.job.company.company_name if app.job.company else "Unknown",
        } if app.job else None,
    }
