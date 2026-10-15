# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/applications/service.py
# Purpose : Domain & persistence logic for Candidate Job Applications
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from shared.models import User, JobSeekerProfile, JobSeekerResume, JobPosting, JobApplication
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger
from shared.utils.resume_storage import (
    MAX_RESUMES_PER_SEEKER,
    read_upload_bytes,
    save_resume_bytes,
)
from services.jobseeker_service.app.api.profile import resume_service

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
    """Check if candidate already submitted an active application for this vacancy."""
    existing = db.query(JobApplication).filter(
        JobApplication.job_id == job_id,
        JobApplication.jobseeker_id == profile_id,
        JobApplication.status != "withdrawn",
    ).first()
    return existing is not None


@service_error_handler
def resolve_application_resume(
    db: Session,
    profile: JobSeekerProfile,
    resume_id: Optional[int] = None,
    resume_url: Optional[str] = None,
    upload_file=None,
    save_to_profile: bool = True,
) -> tuple[str, Optional[int]]:
    """Return (file_url, resume_id) for a new application."""
    resume_service.ensure_legacy_resume(db, profile)

    if upload_file is not None and getattr(upload_file, "filename", None):
        filename = upload_file.filename or "resume.pdf"
        data = read_upload_bytes(upload_file)
        count = resume_service.list_resumes_payload(db, profile)["count"]
        if save_to_profile and count < MAX_RESUMES_PER_SEEKER:
            row = resume_service.add_resume_from_bytes(
                db,
                profile,
                filename,
                data,
                make_default=False,
            )
            return row.file_url, row.id
        file_url, _, _, _ = save_resume_bytes(profile.id, filename, data, subdir="applications")
        return file_url, None

    if resume_id:
        row = resume_service.get_owned_resume(db, profile, resume_id)
        return row.file_url, row.id

    default = resume_service.get_default_resume(db, profile)
    if default:
        return default.file_url, default.id

    # Backwards-compatibility fallbacks for JSON-only clients that pass resume_url
    # directly (the original apply endpoint before the library was introduced).
    # These extra steps are intentionally beyond the spec's 4-step resolution table
    # so that existing callers which never used the library still work without error.
    # Note: get_default_resume above already calls ensure_legacy_resume which seeds
    # a library row from profile.resume_url when the library is empty, so these
    # branches are only reachable in edge cases where seeding failed or was bypassed.
    if resume_url and str(resume_url).strip():
        return str(resume_url).strip(), None

    if profile.resume_url and str(profile.resume_url).strip():
        return profile.resume_url.strip(), None

    raise HTTPException(status_code=400, detail="Please add a résumé before applying.")


def create_application(
    db: Session,
    job: JobPosting,
    profile: JobSeekerProfile,
    cover_letter: Optional[str] = None,
    resume_url: Optional[str] = None,
    resume_id: Optional[int] = None,
    upload_file=None,
    save_to_profile: bool = True,
) -> tuple[JobApplication, Optional[int]]:
    """Create job application record and increment counter."""
    resolved_resume, resolved_id = resolve_application_resume(
        db,
        profile,
        resume_id=resume_id,
        resume_url=resume_url,
        upload_file=upload_file,
        save_to_profile=save_to_profile,
    )

    existing_withdrawn = db.query(JobApplication).filter(
        JobApplication.job_id == job.id,
        JobApplication.jobseeker_id == profile.id,
        JobApplication.status == "withdrawn",
    ).first()

    if existing_withdrawn:
        existing_withdrawn.cover_letter = cover_letter
        existing_withdrawn.resume_url = resolved_resume
        existing_withdrawn.status = "applied"
        job.applications_count = (job.applications_count or 0) + 1
        db.commit()
        db.refresh(existing_withdrawn)
        logger.info(f"Re-activated withdrawn application id={existing_withdrawn.id} for job_id={job.id} by profile_id={profile.id}")
        return existing_withdrawn, resolved_id

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
    return application, resolved_id


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
            "resume_url": app.resume_url,
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

    resume_id = None
    if app.resume_url:
        match = (
            db.query(JobSeekerResume)
            .filter(
                JobSeekerResume.jobseeker_id == profile_id,
                JobSeekerResume.file_url == app.resume_url,
            )
            .first()
        )
        if match:
            resume_id = match.id

    return {
        "id": app.id,
        "status": app.status,
        "cover_letter": app.cover_letter,
        "resume_url": app.resume_url,
        "resume_id": resume_id,
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


@service_error_handler
def withdraw_application(db: Session, application_id: int, profile_id: int) -> JobApplication:
    """Withdraw an application if currently in 'applied' status (BR-301-04)."""
    app = db.query(JobApplication).filter(
        JobApplication.id == application_id,
        JobApplication.jobseeker_id == profile_id,
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    status_lower = (app.status or "").lower()
    if status_lower == "withdrawn":
        raise HTTPException(status_code=400, detail="Application has already been withdrawn")

    # BR-301-04: Talent can withdraw application before screening stage only (applied status)
    if status_lower != "applied":
        raise HTTPException(
            status_code=400,
            detail="Applications can only be withdrawn while in 'applied' status before employer screening begins (BR-301-04)."
        )

    app.status = "withdrawn"
    if app.job and (app.job.applications_count or 0) > 0:
        app.job.applications_count = max(0, (app.job.applications_count or 1) - 1)

    db.commit()
    db.refresh(app)
    logger.info(f"Application id={app.id} withdrawn by profile_id={profile_id}")
    return app

