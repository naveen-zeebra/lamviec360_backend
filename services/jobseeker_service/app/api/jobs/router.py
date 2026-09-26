from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from shared.database.session import get_db
from shared.models import JobPosting, CompanyProfile
from shared.schemas import PaginatedResponse, APIResponse
from shared.utils import paginated_response, success_response

router = APIRouter(prefix="/jobs", tags=["Job Search & Discovery"])

@router.get("", response_model=PaginatedResponse[dict])
def search_jobs(
    keyword: Optional[str] = Query(None, description="Search by title, description or skills"),
    city: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None, description="Full-time, Part-time, Contract, Internship"),
    workplace_type: Optional[str] = Query(None, description="On-site, Hybrid, Remote"),
    experience_level: Optional[str] = Query(None, description="Junior, Mid-level, Senior, Lead"),
    min_salary: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
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

    items = []
    for job in jobs:
        items.append({
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
            "created_at": job.created_at,
            "company": {
                "id": job.company.id,
                "company_name": job.company.company_name,
                "logo_url": job.company.logo_url,
                "industry": job.company.industry,
                "verification_status": job.company.verification_status,
                "is_featured": job.company.is_featured,
            } if job.company else None,
        })

    return paginated_response(
        items=items,
        total_items=total_items,
        page=page,
        page_size=page_size,
        message="Jobs retrieved successfully",
    )


@router.get("/{job_id}", response_model=APIResponse[dict])
def get_job_details(job_id: int, db: Session = Depends(get_db)):
    job = db.query(JobPosting).filter(
        JobPosting.id == job_id,
        JobPosting.is_deleted == False,
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")

    # Increment views count
    job.views_count += 1
    db.commit()

    return success_response(
        data={
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
            "created_at": job.created_at,
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
    )
