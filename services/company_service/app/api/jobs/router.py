from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc

from shared.database.session import get_db
from shared.models import User, CompanyProfile, JobPosting
from shared.schemas import (
    JobPostingCreate,
    JobPostingUpdate,
    PaginatedResponse,
    APIResponse,
)
from shared.utils import (
    get_current_user,
    require_user_type,
    success_response,
    paginated_response,
    log_audit_event,
)

router = APIRouter(prefix="/jobs", tags=["Company Job Management"])

@router.get("", response_model=PaginatedResponse[dict])
def list_company_jobs(
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = user.company_profile
    if not profile:
        return paginated_response(items=[], total_items=0, page=page, page_size=page_size)

    query = db.query(JobPosting).filter(
        JobPosting.company_id == profile.id,
        JobPosting.is_deleted == False,
    )
    if status_filter:
        query = query.filter(JobPosting.status == status_filter)

    total_items = query.count()
    offset = (page - 1) * page_size
    jobs = query.order_by(desc(JobPosting.created_at)).offset(offset).limit(page_size).all()

    items = []
    for j in jobs:
        items.append({
            "id": j.id,
            "title": j.title,
            "job_type": j.job_type,
            "workplace_type": j.workplace_type,
            "experience_level": j.experience_level,
            "city": j.city,
            "salary_min": float(j.salary_min) if j.salary_min else None,
            "salary_max": float(j.salary_max) if j.salary_max else None,
            "salary_currency": j.salary_currency,
            "status": j.status,
            "moderation_status": j.moderation_status,
            "views_count": j.views_count,
            "applications_count": j.applications_count,
            "created_at": j.created_at,
        })

    return paginated_response(
        items=items,
        total_items=total_items,
        page=page,
        page_size=page_size,
        message="Company jobs retrieved",
    )


@router.post("", response_model=APIResponse[dict])
def create_job_posting(
    data: JobPostingCreate,
    request: Request,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = user.company_profile
    if not profile:
        profile = CompanyProfile(user_id=user.id, company_name=user.full_name)
        db.add(profile)
        db.flush()

    job = JobPosting(
        company_id=profile.id,
        title=data.title,
        description=data.description,
        requirements=data.requirements,
        benefits=data.benefits,
        job_type=data.job_type,
        workplace_type=data.workplace_type,
        experience_level=data.experience_level,
        city=data.city,
        country=data.country,
        salary_min=data.salary_min,
        salary_max=data.salary_max,
        salary_currency=data.salary_currency,
        is_negotiable=data.is_negotiable,
        required_skills=data.required_skills,
        status="active",
        moderation_status="approved",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    log_audit_event(
        db,
        action="CREATE_JOB",
        module="COMPANY_JOBS",
        description=f"Company {profile.company_name} created job '{job.title}' (ID {job.id})",
        user_id=user.id,
        user_email=user.email,
        user_type=user.user_type,
        request=request,
    )

    return success_response(
        data={"id": job.id, "title": job.title, "status": job.status},
        message="Job posting created successfully",
    )


@router.get("/{job_id}", response_model=APIResponse[dict])
def get_company_job(
    job_id: int,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = user.company_profile
    job = db.query(JobPosting).filter(
        JobPosting.id == job_id,
        JobPosting.company_id == profile.id if profile else False,
        JobPosting.is_deleted == False,
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")

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
        }
    )


@router.put("/{job_id}", response_model=APIResponse[dict])
def update_company_job(
    job_id: int,
    data: JobPostingUpdate,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = user.company_profile
    job = db.query(JobPosting).filter(
        JobPosting.id == job_id,
        JobPosting.company_id == profile.id if profile else False,
        JobPosting.is_deleted == False,
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")

    for field, value in data.dict(exclude_unset=True).items():
        setattr(job, field, value)

    db.commit()
    db.refresh(job)

    return success_response(data={"id": job.id, "title": job.title}, message="Job updated successfully")


@router.patch("/{job_id}/status", response_model=APIResponse[dict])
def toggle_job_status(
    job_id: int,
    status_val: str = Query(..., alias="status", pattern="^(active|closed|draft)$"),
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = user.company_profile
    job = db.query(JobPosting).filter(
        JobPosting.id == job_id,
        JobPosting.company_id == profile.id if profile else False,
        JobPosting.is_deleted == False,
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")

    job.status = status_val
    db.commit()

    return success_response(message=f"Job status updated to {status_val}")


@router.delete("/{job_id}", response_model=APIResponse[None])
def delete_company_job(
    job_id: int,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = user.company_profile
    job = db.query(JobPosting).filter(
        JobPosting.id == job_id,
        JobPosting.company_id == profile.id if profile else False,
        JobPosting.is_deleted == False,
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")

    job.is_deleted = True
    db.commit()

    return success_response(message="Job posting deleted successfully")
