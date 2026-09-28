# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/jobs/service.py
# Purpose : Domain & query logic for Job Seeker Job Search & Discovery
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from shared.models import JobPosting
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("jobseeker_jobs_service")


def serialize_job_summary(job: JobPosting) -> Dict[str, Any]:
    """Serialize summary of job posting."""
    return {
        "id": job.id,
        "title": job.title,
        "job_type": job.job_type,
        "workplace_type": job.workplace_type,
        "experience_level": job.experience_level,
        "city": job.city,
        "country": job.country,
        "salary_min": float(job.salary_min) if job.salary_min else None,
        "salary_max": float(job.salary_max) if job.salary_max else None,
        "salary_currency": job.salary_currency,
        "is_negotiable": job.is_negotiable,
        "required_skills": job.required_skills,
        "views_count": job.views_count,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "company": {
            "id": job.company.id,
            "company_name": job.company.company_name,
            "logo_url": job.company.logo_url,
            "industry": job.company.industry,
            "verification_status": job.company.verification_status,
            "is_featured": job.company.is_featured,
        } if job.company else None,
    }


def serialize_job_detail(job: JobPosting) -> Dict[str, Any]:
    """Serialize full job details."""
    return {
        "id": job.id,
        "title": job.title,
        "description": job.description,
        "requirements": job.requirements,
        "benefits": job.benefits,
        "job_type": job.job_type,
        "workplace_type": job.workplace_type,
        "experience_level": job.experience_level,
        "city": job.city,
        "country": job.country,
        "salary_min": float(job.salary_min) if job.salary_min else None,
        "salary_max": float(job.salary_max) if job.salary_max else None,
        "salary_currency": job.salary_currency,
        "is_negotiable": job.is_negotiable,
        "required_skills": job.required_skills,
        "status": job.status,
        "moderation_status": job.moderation_status,
        "views_count": job.views_count,
        "applications_count": job.applications_count,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "company": {
            "id": job.company.id,
            "company_name": job.company.company_name,
            "logo_url": job.company.logo_url,
            "cover_image_url": job.company.cover_image_url,
            "website": job.company.website,
            "industry": job.company.industry,
            "company_size": job.company.company_size,
            "about": job.company.about,
            "address": job.company.address,
            "city": job.company.city,
            "verification_status": job.company.verification_status,
            "is_featured": job.company.is_featured,
        } if job.company else None,
    }


@service_error_handler
def search_published_jobs(
    db: Session,
    keyword: Optional[str] = None,
    city: Optional[str] = None,
    job_type: Optional[str] = None,
    workplace_type: Optional[str] = None,
    experience_level: Optional[str] = None,
    min_salary: Optional[float] = None,
    page: int = 1,
    page_size: int = 10,
) -> Tuple[List[Dict[str, Any]], int]:
    """Query published and approved jobs with keyword, location, salary filters."""
    query = db.query(JobPosting).filter(
        JobPosting.status == "published",
        JobPosting.moderation_status == "approved",
        JobPosting.is_deleted == False,
    )

    if keyword:
        term = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                JobPosting.title.ilike(term),
                JobPosting.description.ilike(term),
                JobPosting.required_skills.ilike(term),
            )
        )

    if city:
        query = query.filter(JobPosting.city.ilike(f"%{city.strip()}%"))

    if job_type:
        query = query.filter(JobPosting.job_type == job_type)

    if workplace_type:
        query = query.filter(JobPosting.workplace_type == workplace_type)

    if experience_level:
        query = query.filter(JobPosting.experience_level == experience_level)

    if min_salary:
        query = query.filter(JobPosting.salary_min >= min_salary)

    total_items = query.count()
    offset = (page - 1) * page_size
    jobs = query.order_by(desc(JobPosting.created_at)).offset(offset).limit(page_size).all()

    items = [serialize_job_summary(j) for j in jobs]
    return items, total_items


@service_error_handler
def get_job_and_increment_view(db: Session, job_id: int) -> Optional[JobPosting]:
    """Retrieve job posting and increment view count."""
    job = db.query(JobPosting).filter(
        JobPosting.id == job_id,
        JobPosting.is_deleted == False,
    ).first()

    if job:
        job.views_count = (job.views_count or 0) + 1
        db.commit()
        db.refresh(job)
    return job
