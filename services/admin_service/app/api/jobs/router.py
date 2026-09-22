from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel

from shared.database.session import get_db
from shared.models import JobPosting, User
from shared.schemas import PaginatedResponse, APIResponse
from shared.utils import (
    get_current_user,
    require_roles,
    success_response,
    paginated_response,
    log_audit_event,
)

router = APIRouter(prefix="/jobs", tags=["Admin Job Moderation"])

class JobModerationRequest(BaseModel):
    moderation_status: str  # approved, rejected, pending
    moderation_notes: Optional[str] = None

@router.get("", response_model=PaginatedResponse[dict])
def list_all_jobs(
    moderation_status: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    query = db.query(JobPosting).filter(JobPosting.is_deleted == False)

    if moderation_status:
        query = query.filter(JobPosting.moderation_status == moderation_status)
    if status_filter:
        query = query.filter(JobPosting.status == status_filter)
    if search:
        query = query.filter(JobPosting.title.ilike(f"%{search.strip()}%"))

    total_items = query.count()
    offset = (page - 1) * page_size
    jobs = query.order_by(desc(JobPosting.created_at)).offset(offset).limit(page_size).all()

    items = []
    for j in jobs:
        items.append({
            "id": j.id,
            "title": j.title,
            "company_name": j.company.company_name if j.company else "Unknown",
            "job_type": j.job_type,
            "workplace_type": j.workplace_type,
            "experience_level": j.experience_level,
            "city": j.city,
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
        message="Jobs retrieved",
    )


@router.get("/{job_id}", response_model=APIResponse[dict])
def get_job_detail(
    job_id: int,
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    j = db.query(JobPosting).filter(JobPosting.id == job_id, JobPosting.is_deleted == False).first()
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")

    return success_response(
        data={
            "id": j.id,
            "title": j.title,
            "description": j.description,
            "requirements": j.requirements,
            "benefits": j.benefits,
            "job_type": j.job_type,
            "workplace_type": j.workplace_type,
            "experience_level": j.experience_level,
            "city": j.city,
            "country": j.country,
            "salary_min": float(j.salary_min) if j.salary_min else None,
            "salary_max": float(j.salary_max) if j.salary_max else None,
            "salary_currency": j.salary_currency,
            "status": j.status,
            "moderation_status": j.moderation_status,
            "moderation_notes": j.moderation_notes,
            "views_count": j.views_count,
            "applications_count": j.applications_count,
            "created_at": j.created_at,
            "company": {
                "id": j.company.id,
                "name": j.company.company_name,
                "verification_status": j.company.verification_status,
            } if j.company else None,
        }
    )


@router.patch("/{job_id}/moderate", response_model=APIResponse[dict])
def moderate_job(
    job_id: int,
    data: JobModerationRequest,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    j = db.query(JobPosting).filter(JobPosting.id == job_id, JobPosting.is_deleted == False).first()
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")

    j.moderation_status = data.moderation_status
    if data.moderation_notes is not None:
        j.moderation_notes = data.moderation_notes

    db.commit()

    log_audit_event(
        db,
        action="MODERATE_JOB",
        module="ADMIN_JOBS",
        description=f"Admin {current_admin.email} moderated job '{j.title}' to {data.moderation_status}",
        user_id=current_admin.id,
        user_email=current_admin.email,
        user_type=current_admin.user_type,
        request=request,
    )

    return success_response(
        data={"id": j.id, "moderation_status": j.moderation_status},
        message=f"Job moderation status updated to {data.moderation_status}",
    )


@router.delete("/{job_id}", response_model=APIResponse[None])
def delete_job(
    job_id: int,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
):
    j = db.query(JobPosting).filter(JobPosting.id == job_id, JobPosting.is_deleted == False).first()
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")

    j.is_deleted = True
    db.commit()

    log_audit_event(
        db,
        action="DELETE_JOB",
        module="ADMIN_JOBS",
        description=f"Admin {current_admin.email} removed job '{j.title}'",
        user_id=current_admin.id,
        user_email=current_admin.email,
        user_type=current_admin.user_type,
        request=request,
    )

    return success_response(message="Job deleted successfully")
