# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/jobs/router.py
# Purpose : Presentation layer (FastAPI endpoints) for Job Seeker Job Search
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import User
from shared.schemas import PaginatedResponse, APIResponse
from shared.utils import paginated_response, success_response, decode_token

from .schemas import JobReportCreateSchema
from .controller import (
    search_jobs_controller,
    get_job_details_controller,
    create_job_report_controller,
)

router = APIRouter(prefix="/jobs", tags=["Job Search & Discovery"])


@router.get("", response_model=PaginatedResponse[dict], summary="Search Published Jobs")
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
    items, total_items = search_jobs_controller(
        keyword=keyword,
        city=city,
        job_type=job_type,
        workplace_type=workplace_type,
        experience_level=experience_level,
        min_salary=min_salary,
        page=page,
        page_size=page_size,
        db=db,
    )
    return paginated_response(
        items=items,
        total_items=total_items,
        page=page,
        page_size=page_size,
        message="Jobs retrieved successfully",
    )


@router.get("/{job_id}", response_model=APIResponse[dict], summary="Get Job Details")
def get_job_details(job_id: int, db: Session = Depends(get_db)):
    data = get_job_details_controller(job_id, db)
    return success_response(data=data)


@router.post("/{job_id}/report", response_model=APIResponse[dict], summary="Report a Job Posting")
def report_job(
    job_id: int,
    data: JobReportCreateSchema,
    request: Request,
    db: Session = Depends(get_db),
):
    """Submit a policy / compliance report on a job posting."""
    current_user = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        try:
            payload = decode_token(token)
            uid = payload.get("sub")
            if uid:
                current_user = db.query(User).filter(User.id == int(uid)).first()
        except Exception:
            pass

    res = create_job_report_controller(job_id=job_id, data=data, db=db, current_user=current_user)
    return success_response(data=res, message="Report submitted successfully")

