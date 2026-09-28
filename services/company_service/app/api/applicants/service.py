# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/applicants/service.py
# Purpose : Domain & persistence logic for ATS Applicant Management
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, or_, func

from shared.models import User, CompanyProfile, JobPosting, JobApplication, JobSeekerProfile
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("company_applicants_service")

# Canonical Stage Mapping between backend status values and ATS display labels
STAGE_CANONICAL_MAP: Dict[str, str] = {
    "applied": "Applied",
    "screening": "Screening",
    "reviewing": "Screening",
    "shortlisted": "Shortlisted",
    "interviewing": "Interview Scheduled",
    "interview": "Interview Scheduled",
    "interview scheduled": "Interview Scheduled",
    "offer_sent": "Offer Sent",
    "offer": "Offer Sent",
    "offer sent": "Offer Sent",
    "hired": "Hired",
    "rejected": "Rejected",
}

STAGE_FILTER_EXPANSION: Dict[str, List[str]] = {
    "applied": ["applied", "Applied"],
    "screening": ["screening", "reviewing", "Screening"],
    "shortlisted": ["shortlisted", "Shortlisted"],
    "interview scheduled": ["interview scheduled", "interviewing", "interview", "Interview Scheduled"],
    "interviewing": ["interview scheduled", "interviewing", "interview", "Interview Scheduled"],
    "offer sent": ["offer sent", "offer", "offer_sent", "Offer Sent"],
    "offer_sent": ["offer sent", "offer", "offer_sent", "Offer Sent"],
    "hired": ["hired", "Hired"],
    "rejected": ["rejected", "Rejected"],
}


@service_error_handler
def get_company_tenant(user: User) -> Optional[CompanyProfile]:
    """Retrieve company profile for user."""
    return user.company_profile


@service_error_handler
def get_company_stage_counts(
    db: Session,
    company_id: int,
    job_id: Optional[int] = None,
) -> Dict[str, int]:
    """Return application counts grouped by ATS pipeline stage for high-volume pipelines."""
    query = (
        db.query(JobApplication.status, func.count(JobApplication.id))
        .join(JobPosting, JobApplication.job_id == JobPosting.id)
        .filter(JobPosting.company_id == company_id, JobPosting.is_deleted == False)
    )
    if job_id:
        query = query.filter(JobApplication.job_id == job_id)

    raw_counts = query.group_by(JobApplication.status).all()

    counts: Dict[str, int] = {
        "Total": 0,
        "Applied": 0,
        "Screening": 0,
        "Shortlisted": 0,
        "Interview Scheduled": 0,
        "Offer Sent": 0,
        "Hired": 0,
        "Rejected": 0,
    }

    for status_val, count in raw_counts:
        key = (status_val or "").lower().strip()
        canonical = STAGE_CANONICAL_MAP.get(key, "Applied")
        counts[canonical] = counts.get(canonical, 0) + count
        counts["Total"] += count

    return counts


@service_error_handler
def list_company_applicants(
    db: Session,
    company_id: int,
    job_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    min_score: Optional[int] = None,
    sort_by: Optional[str] = "date",
    sort_order: Optional[str] = "desc",
    page: int = 1,
    page_size: int = 25,
) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieve paginated candidate applications belonging to this company's jobs with enterprise filtering and search."""
    query = (
        db.query(JobApplication)
        .join(JobPosting, JobApplication.job_id == JobPosting.id)
        .outerjoin(JobSeekerProfile, JobApplication.jobseeker_id == JobSeekerProfile.id)
        .outerjoin(User, JobSeekerProfile.user_id == User.id)
        .filter(JobPosting.company_id == company_id, JobPosting.is_deleted == False)
    )

    if job_id:
        query = query.filter(JobApplication.job_id == job_id)

    if status_filter and status_filter.lower() != "all":
        norm_key = status_filter.lower().strip()
        allowed_statuses = STAGE_FILTER_EXPANSION.get(norm_key, [status_filter])
        query = query.filter(
            or_(
                JobApplication.status.in_(allowed_statuses),
                func.lower(JobApplication.status) == norm_key,
            )
        )

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.full_name.ilike(term),
                User.email.ilike(term),
                JobSeekerProfile.headline.ilike(term),
                JobSeekerProfile.skills.ilike(term),
                JobPosting.title.ilike(term),
            )
        )

    if min_score is not None and min_score > 0:
        min_rating = max(1, round(min_score / 20))
        query = query.filter(JobApplication.rating >= min_rating)

    total_items = query.count()

    is_asc = (sort_order or "desc").lower() == "asc"
    order_fn = asc if is_asc else desc

    if sort_by in ("score", "rating"):
        query = query.order_by(order_fn(JobApplication.rating), desc(JobApplication.created_at))
    elif sort_by == "experience":
        query = query.order_by(order_fn(JobSeekerProfile.experience_years), desc(JobApplication.created_at))
    elif sort_by == "name":
        query = query.order_by(order_fn(User.full_name))
    else:
        query = query.order_by(order_fn(JobApplication.created_at))

    offset = (page - 1) * page_size
    applications = query.offset(offset).limit(page_size).all()

    items = []
    for app in applications:
        seeker = app.jobseeker
        seeker_user = seeker.user if seeker else None
        candidate_name = seeker_user.full_name if seeker_user else "Anonymous"
        candidate_email = seeker_user.email if seeker_user else None
        candidate_phone = seeker_user.phone if seeker_user else ""
        exp_years = float(seeker.experience_years or 0) if seeker else 0.0

        calc_score = (app.rating * 20) if (app.rating and app.rating > 0) else 85
        raw_status = (app.status or "applied").strip()
        canonical_stage = STAGE_CANONICAL_MAP.get(raw_status.lower(), raw_status.title())

        skills_list = []
        if seeker and seeker.skills:
            if isinstance(seeker.skills, list):
                skills_list = seeker.skills
            elif isinstance(seeker.skills, str):
                skills_list = [s.strip() for s in seeker.skills.split(",") if s.strip()]

        clean_name = candidate_name.replace(" ", "_") if candidate_name else "Candidate"
        default_resume = f"/uploads/resumes/{clean_name}_CV.pdf"
        resolved_resume = app.resume_url or (seeker.resume_url if seeker else None) or default_resume
        resume_file_name = resolved_resume.split("/")[-1] if resolved_resume else f"{clean_name}_Resume.pdf"

        items.append({
            "id": app.id,
            "job_id": app.job_id,
            "job_title": app.job.title if app.job else "Unknown Job",
            "candidate_name": candidate_name,
            "candidate_email": candidate_email,
            "candidate_phone": candidate_phone,
            "candidate_headline": seeker.headline if seeker else None,
            "candidate_skills": skills_list,
            "candidate_experience_years": exp_years,
            "education_level": "Bachelor's Degree",
            "resume_url": resolved_resume,
            "resumeUrl": resolved_resume,
            "resume_file_name": resume_file_name,
            "resumeFileName": resume_file_name,
            "cover_letter": app.cover_letter,
            "status": app.status,
            "stage": canonical_stage,
            "rating": app.rating or 4,
            "match_score": calc_score,
            "matchScore": calc_score,
            "recruiter_notes": app.recruiter_notes,
            "notes": [{"id": 1, "text": app.recruiter_notes, "author": "Recruiter", "at": app.created_at.strftime("%Y-%m-%d")}] if app.recruiter_notes else [],
            "applied_at": app.created_at.isoformat() if app.created_at else None,
            "applied_date": app.created_at.strftime("%Y-%m-%d") if app.created_at else None,
            # Frontend compatibility fields
            "name": candidate_name,
            "email": candidate_email,
            "phone": candidate_phone,
            "jobId": app.job_id,
            "jobTitle": app.job.title if app.job else "",
            "experienceYears": exp_years,
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

    raw_status = (app.status or "applied").strip()
    canonical_stage = STAGE_CANONICAL_MAP.get(raw_status.lower(), raw_status.title())

    calc_score = (app.rating * 20) if (app.rating and app.rating > 0) else 85

    skills_list = []
    if seeker and seeker.skills:
        if isinstance(seeker.skills, list):
            skills_list = seeker.skills
        elif isinstance(seeker.skills, str):
            skills_list = [s.strip() for s in seeker.skills.split(",") if s.strip()]

    return {
        "id": app.id,
        "job_id": app.job_id,
        "job_title": app.job.title if app.job else "",
        "status": app.status,
        "stage": canonical_stage,
        "rating": app.rating,
        "matchScore": calc_score,
        "match_score": calc_score,
        "recruiter_notes": app.recruiter_notes,
        "notes": [{"id": 1, "text": app.recruiter_notes, "author": "Recruiter", "at": app.created_at.strftime("%Y-%m-%d")}] if app.recruiter_notes else [],
        "cover_letter": app.cover_letter,
        "resume_url": app.resume_url or (seeker.resume_url if seeker else None) or f"/uploads/resumes/{(seeker_user.full_name.replace(' ', '_') if (seeker_user and seeker_user.full_name) else 'Candidate')}_CV.pdf",
        "resumeUrl": app.resume_url or (seeker.resume_url if seeker else None) or f"/uploads/resumes/{(seeker_user.full_name.replace(' ', '_') if (seeker_user and seeker_user.full_name) else 'Candidate')}_CV.pdf",
        "resume_file_name": (app.resume_url or (seeker.resume_url if seeker else None) or f"{(seeker_user.full_name.replace(' ', '_') if (seeker_user and seeker_user.full_name) else 'Candidate')}_Resume.pdf").split("/")[-1],
        "resumeFileName": (app.resume_url or (seeker.resume_url if seeker else None) or f"{(seeker_user.full_name.replace(' ', '_') if (seeker_user and seeker_user.full_name) else 'Candidate')}_Resume.pdf").split("/")[-1],
        "applied_at": app.created_at.isoformat() if app.created_at else None,
        "applied_date": app.created_at.strftime("%Y-%m-%d") if app.created_at else None,
        "updated_at": app.updated_at.isoformat() if app.updated_at else None,
        "name": seeker_user.full_name if seeker_user else "Anonymous",
        "email": seeker_user.email if seeker_user else "",
        "phone": seeker_user.phone if seeker_user else "",
        "experienceYears": float(seeker.experience_years or 0) if seeker else 0.0,
        "educationLevel": "Bachelor's Degree",
        "candidate": {
            "name": seeker_user.full_name if seeker_user else "",
            "email": seeker_user.email if seeker_user else "",
            "phone": seeker_user.phone if seeker_user else "",
            "headline": seeker.headline if seeker else "",
            "bio": seeker.bio if seeker else "",
            "skills": skills_list,
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
    logger.info(f"Updated application id={app.id} to status='{status}', rating={rating}")
    return app


@service_error_handler
def bulk_update_applicant_stage(
    db: Session,
    company_id: int,
    application_ids: List[Any],
    status: str,
    rejection_note: Optional[str] = None,
) -> int:
    """Bulk update applicant stage safely supporting string or int ids."""
    clean_ids: List[int] = []
    for aid in application_ids:
        try:
            clean_ids.append(int(aid))
        except (ValueError, TypeError):
            pass

    if not clean_ids:
        return 0

    apps = (
        db.query(JobApplication)
        .join(JobPosting, JobApplication.job_id == JobPosting.id)
        .filter(JobApplication.id.in_(clean_ids), JobPosting.company_id == company_id)
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
    if app.recruiter_notes:
        app.recruiter_notes = f"{app.recruiter_notes}\n{note}"
    else:
        app.recruiter_notes = note
    db.commit()
    logger.info(f"Added note to application id={app.id}")


@service_error_handler
def schedule_candidate_interview(db: Session, app: JobApplication, interview_data: Dict[str, Any]) -> None:
    """Set application stage to interviewing."""
    app.status = "interviewing"
    db.commit()
    logger.info(f"Scheduled interview for application id={app.id}")
