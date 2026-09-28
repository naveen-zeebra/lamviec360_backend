# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/applicants/service.py
# Purpose : Domain & persistence logic for ATS Applicant Management
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from shared.models import User, CompanyProfile, JobPosting, JobApplication
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("company_applicants_service")


@service_error_handler
def get_company_tenant(user: User) -> Optional[CompanyProfile]:
    """Retrieve company profile for user."""
    return user.company_profile


@service_error_handler
def list_company_applicants(
    db: Session,
    company_id: int,
    job_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieve paginated candidate applications belonging to this company's jobs."""
    query = (
        db.query(JobApplication)
        .join(JobPosting, JobApplication.job_id == JobPosting.id)
        .filter(JobPosting.company_id == company_id, JobPosting.is_deleted == False)
    )

    if job_id:
        query = query.filter(JobApplication.job_id == job_id)
    if status_filter:
        query = query.filter(JobApplication.status == status_filter)

    total_items = query.count()
    offset = (page - 1) * page_size
    applications = query.order_by(desc(JobApplication.created_at)).offset(offset).limit(page_size).all()

    items = []
    for app in applications:
        seeker = app.jobseeker
        seeker_user = seeker.user if seeker else None
        candidate_name = seeker_user.full_name if seeker_user else "Anonymous"
        candidate_email = seeker_user.email if seeker_user else None
        candidate_phone = seeker_user.phone if seeker_user else ""
        exp_years = float(seeker.experience_years or 0) if seeker else 0.0

        items.append({
            "id": app.id,
            "job_id": app.job_id,
            "job_title": app.job.title if app.job else "Unknown Job",
            "candidate_name": candidate_name,
            "candidate_email": candidate_email,
            "candidate_phone": candidate_phone,
            "candidate_headline": seeker.headline if seeker else None,
            "candidate_skills": seeker.skills if seeker else None,
            "candidate_experience_years": exp_years,
            "resume_url": app.resume_url or (seeker.resume_url if seeker else None),
            "cover_letter": app.cover_letter,
            "status": app.status,
            "rating": app.rating,
            "recruiter_notes": app.recruiter_notes,
            "applied_at": app.created_at.isoformat() if app.created_at else None,
            # Frontend compatibility fields
            "name": candidate_name,
            "email": candidate_email,
            "phone": candidate_phone,
            "stage": app.status,
            "experience_years": exp_years,
            "applied_date": app.created_at.strftime("%Y-%m-%d") if app.created_at else None,
        })

    return items, total_items


@service_error_handler
def get_applicant_by_id(db: Session, company_id: int, application_id: int) -> Optional[JobApplication]:
    """Find a specific application for a company's job."""
    return (
        db.query(JobApplication)
        .join(JobPosting, JobApplication.job_id == JobPosting.id)
        .filter(JobApplication.id == application_id, JobPosting.company_id == company_id)
        .first()
    )


def serialize_applicant_detail(app: JobApplication) -> Dict[str, Any]:
    """Serialize detailed candidate view."""
    seeker = app.jobseeker
    seeker_user = seeker.user if seeker else None

    return {
        "id": app.id,
        "job_id": app.job_id,
        "job_title": app.job.title if app.job else "",
        "status": app.status,
        "rating": app.rating,
        "recruiter_notes": app.recruiter_notes,
        "cover_letter": app.cover_letter,
        "resume_url": app.resume_url,
        "applied_at": app.created_at.isoformat() if app.created_at else None,
        "updated_at": app.updated_at.isoformat() if app.updated_at else None,
        "candidate": {
            "name": seeker_user.full_name if seeker_user else "",
            "email": seeker_user.email if seeker_user else "",
            "phone": seeker_user.phone if seeker_user else "",
            "headline": seeker.headline if seeker else "",
            "bio": seeker.bio if seeker else "",
            "skills": seeker.skills if seeker else "",
            "experience_years": float(seeker.experience_years or 0) if seeker else 0.0,
            "city": seeker.city if seeker else "",
            "country": seeker.country if seeker else "",
            "github_url": seeker.github_url if seeker else "",
            "linkedin_url": seeker.linkedin_url if seeker else "",
        } if seeker else None,
    }


@service_error_handler
def update_applicant_status_and_notes(
    db: Session,
    app: JobApplication,
    status: str,
    notes: Optional[str] = None,
    rating: Optional[int] = None,
) -> JobApplication:
    """Update status, rating, and notes on application."""
    app.status = status
    if notes is not None:
        app.recruiter_notes = notes
    if rating is not None:
        app.rating = rating
    db.commit()
    logger.info(f"Updated application id={app.id} to status='{status}'")
    return app


@service_error_handler
def bulk_update_applicant_stage(
    db: Session,
    company_id: int,
    application_ids: List[int],
    status: str,
    rejection_note: Optional[str] = None,
) -> int:
    """Bulk update applicant stage."""
    apps = (
        db.query(JobApplication)
        .join(JobPosting, JobApplication.job_id == JobPosting.id)
        .filter(JobApplication.id.in_(application_ids), JobPosting.company_id == company_id)
        .all()
    )
    for app in apps:
        app.status = status
        if rejection_note:
            app.recruiter_notes = rejection_note
    db.commit()
    logger.info(f"Bulk updated {len(apps)} applications to status='{status}'")
    return len(apps)


@service_error_handler
def add_candidate_recruiter_note(db: Session, app: JobApplication, note: str) -> None:
    """Append or set recruiter note."""
    app.recruiter_notes = note
    db.commit()
    logger.info(f"Added note to application id={app.id}")


@service_error_handler
def schedule_candidate_interview(db: Session, app: JobApplication, interview_data: Dict[str, Any]) -> None:
    """Set application stage to interviewing."""
    app.status = "interviewing"
    db.commit()
    logger.info(f"Scheduled interview for application id={app.id}")
