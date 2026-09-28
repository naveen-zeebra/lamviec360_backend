# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/jobs/router.py
# Purpose : HTTP Routing endpoints for Admin Job Moderation
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import User
from shared.schemas import PaginatedResponse, APIResponse
from shared.utils import require_roles, success_response, paginated_response
from .schemas import JobModerationSchema
from .controller import (
    list_jobs_controller,
    get_job_detail_controller,
    moderate_job_controller,
    delete_job_controller,
)

router = APIRouter(prefix="/jobs", tags=["Admin Job Moderation"])


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
    """Retrieve all jobs across the platform with moderation status filtering."""
    items, total_items = list_jobs_controller(
        db=db,
        moderation_status=moderation_status,
        status_filter=status_filter,
        search=search,
        page=page,
        page_size=page_size,
    )
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
    """Fetch complete detail of a job for moderation review."""
    data = get_job_detail_controller(db=db, job_id=job_id)
    return success_response(data=data)


@router.patch("/{job_id}/moderate", response_model=APIResponse[dict])
def moderate_job(
    job_id: int,
    data: JobModerationSchema,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    """Approve or reject a job posting."""
    res = moderate_job_controller(
        db=db,
        job_id=job_id,
        data=data,
        current_admin=current_admin,
        request=request,
    )
    return success_response(
        data=res,
        message=f"Job moderation status updated to {data.moderation_status}",
    )


@router.delete("/{job_id}", response_model=APIResponse[None])
def delete_job(
    job_id: int,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
):
    """Remove a job posting from the platform (soft delete)."""
    delete_job_controller(
        db=db,
        job_id=job_id,
        current_admin=current_admin,
        request=request,
    )
    return success_response(message="Job deleted successfully")
