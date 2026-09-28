# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/jobs/controller.py
# Purpose : Orchestration layer for Job Seeker Job Search & Discovery
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, Dict, Any, Tuple, List
from fastapi import HTTPException
from sqlalchemy.orm import Session

from shared.utils.logger import get_logger
from . import service

logger = get_logger("jobseeker_jobs_controller")


def search_jobs_controller(
    keyword: Optional[str],
    city: Optional[str],
    job_type: Optional[str],
    workplace_type: Optional[str],
    experience_level: Optional[str],
    min_salary: Optional[float],
    page: int,
    page_size: int,
    db: Session,
) -> Tuple[List[Dict[str, Any]], int]:
    """Execute search across published vacancies."""
    return service.search_published_jobs(
        db=db,
        keyword=keyword,
        city=city,
        job_type=job_type,
        workplace_type=workplace_type,
        experience_level=experience_level,
        min_salary=min_salary,
        page=page,
        page_size=page_size,
    )


def get_job_details_controller(job_id: int, db: Session) -> Dict[str, Any]:
    """Fetch details and increment views."""
    job = service.get_job_and_increment_view(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")
    return service.serialize_job_detail(job)
