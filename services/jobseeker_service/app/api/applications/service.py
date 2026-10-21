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
    """Retrieve active, published, and non-expired job for application (BR-201-09)."""
    from datetime import datetime
    now = datetime.utcnow()
    job = db.query(JobPosting).filter(
        JobPosting.id == job_id,
        JobPosting.status.in_(["active", "published"]),
        JobPosting.is_deleted == False,
    ).first()
    if not job:
        return None
    if job.moderation_status and job.moderation_status != "approved":
        return None
    if job.expires_at:
        exp = job.expires_at.replace(tzinfo=None) if job.expires_at.tzinfo else job.expires_at
        if exp < now:
            return None
    return job


@service_error_handler
def check_existing_application(db: Session, job_id: int, profile_id: int) -> bool:
    """
    Check if candidate already submitted an active application for this vacancy.
    JSP-FR-005b / BR-301-09:
    Candidates who have been rejected cannot reapply to the same job for 90 days.
    """
    existing = (
        db.query(JobApplication)
        .filter(
            JobApplication.job_id == job_id,
            JobApplication.jobseeker_id == profile_id,
            JobApplication.status != "withdrawn",
        )
        .order_by(JobApplication.updated_at.desc())
        .first()
    )

    if not existing:
        return False

    status_lower = (existing.status or "").lower()
    if status_lower == "rejected":
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        ref_time = existing.updated_at or existing.created_at
        if ref_time:
            if ref_time.tzinfo is None:
                ref_time = ref_time.replace(tzinfo=timezone.utc)
            days_passed = (now - ref_time).days
            if days_passed < 90:
                rejection_date = ref_time.strftime("%d/%m/%Y")
                reapply_date = (ref_time + timedelta(days=90)).strftime("%d/%m/%Y")
                raise HTTPException(
                    status_code=400,
                    detail=f"You applied for this position on {rejection_date} and were not selected. You can reapply after {reapply_date} (BR-301-09)."
                )
            else:
                # 90 days have elapsed, reapplication allowed per JSP-FR-005b
                return False

    return True


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
    resume_name: Optional[str] = None,
    consent: bool = True,
) -> tuple[JobApplication, Optional[int]]:
    """Create job application record with consent metadata and completeness gate."""
    # BR-101-02: Profile completeness must be >= 60%
    if profile.user:
        from services.jobseeker_service.app.api.profile.service import compute_profile_completeness
        completeness = compute_profile_completeness(profile.user, profile)
        if completeness < 60:
            raise HTTPException(
                status_code=400,
                detail=f"Please complete your profile to at least 60% before applying (BR-101-02). Current completeness: {completeness}%."
            )

    resolved_resume, resolved_id = resolve_application_resume(
        db,
        profile,
        resume_id=resume_id,
        resume_url=resume_url,
        upload_file=upload_file,
        save_to_profile=save_to_profile,
    )

    # Determine named title
    final_resume_name = resume_name
    if not final_resume_name and resolved_id:
        from shared.models import JobSeekerResume
        res_row = db.query(JobSeekerResume).filter(JobSeekerResume.id == resolved_id).first()
        if res_row:
            final_resume_name = res_row.resume_name or res_row.file_name
    if not final_resume_name and resolved_resume:
        import os
        final_resume_name = os.path.basename(resolved_resume)

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    existing_withdrawn = db.query(JobApplication).filter(
        JobApplication.job_id == job.id,
        JobApplication.jobseeker_id == profile.id,
        JobApplication.status == "withdrawn",
    ).first()

    if existing_withdrawn:
        existing_withdrawn.cover_letter = cover_letter
        existing_withdrawn.resume_url = resolved_resume
        existing_withdrawn.resume_name = final_resume_name
        existing_withdrawn.consent = bool(consent)
        existing_withdrawn.consent_timestamp = now
        existing_withdrawn.status = "applied"
        job.applications_count = (job.applications_count or 0) + 1
        db.commit()
        db.refresh(existing_withdrawn)
        logger.info(f"Re-activated application id={existing_withdrawn.id} for job_id={job.id} by profile_id={profile.id}")
        return existing_withdrawn, resolved_id

    application = JobApplication(
        job_id=job.id,
        jobseeker_id=profile.id,
        cover_letter=cover_letter,
        resume_url=resolved_resume,
        resume_name=final_resume_name,
        consent=bool(consent),
        consent_timestamp=now,
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
        "resume_name": app.resume_name or (match.resume_name if match else None),
        "resume_id": resume_id,
        "consent": getattr(app, "consent", True),
        "consent_timestamp": app.consent_timestamp.isoformat() if getattr(app, "consent_timestamp", None) else None,
        "acknowledgment_sent": getattr(app, "acknowledgment_sent", False),
        "acknowledgment_sent_at": app.acknowledgment_sent_at.isoformat() if getattr(app, "acknowledgment_sent_at", None) else None,
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


@service_error_handler
def dispatch_pending_24h_acknowledgments(db: Session) -> int:
    """
    Find applications submitted within the past 24 hours that haven't received
    their auto-acknowledgment email (BR-301-11), and dispatch the confirmation email.
    Returns the count of emails dispatched.
    """
    from datetime import datetime, timezone, timedelta
    from shared.utils.email import send_application_confirmation_email

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    pending_apps = (
        db.query(JobApplication)
        .filter(
            JobApplication.created_at >= cutoff,
            JobApplication.status == "applied",
            (JobApplication.acknowledgment_sent == False) | (JobApplication.acknowledgment_sent == None),
        )
        .all()
    )

    dispatched = 0
    for app in pending_apps:
        profile = app.jobseeker
        user = profile.user if profile else None
        job = app.job
        if not user or not user.email or not job:
            continue

        company_name = job.company.company_name if job.company else "Company"
        try:
            send_application_confirmation_email(
                to_email=user.email,
                candidate_name=user.full_name,
                job_title=job.title,
                company_name=company_name,
                application_id=app.id,
                applied_at=app.created_at,
                job_location=job.city,
                resume_name=app.resume_name,
            )
            app.acknowledgment_sent = True
            app.acknowledgment_sent_at = datetime.now(timezone.utc)
            dispatched += 1

        except Exception as e:
            logger.warning(f"Failed to dispatch pending confirmation email for app id={app.id}: {e}")

    if dispatched > 0:
        db.commit()

    return dispatched


