# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/jobs/router.py
# Purpose : Presentation layer (FastAPI endpoints) for Company Job Management
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, Any
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.schemas import PaginatedResponse, APIResponse
from shared.utils import get_current_company_user, success_response, paginated_response

from .schemas import CompanyJobCreateRequest, CompanyJobUpdateRequest
from .controller import (
    list_jobs_controller,
    create_job_controller,
    get_job_controller,
    update_job_controller,
    toggle_status_controller,
    duplicate_job_controller,
    delete_job_controller,
)

router = APIRouter(prefix="/jobs", tags=["Company Job Management"])


@router.get("", response_model=PaginatedResponse[dict], summary="List Company Jobs")
def list_company_jobs(
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user: Any = Depends(get_current_company_user),
    db: Session = Depends(get_db),
):
    items, total_items = list_jobs_controller(user, status_filter, page, page_size, db)
    return paginated_response(
        items=items,
        total_items=total_items,
        page=page,
        page_size=page_size,
        message="Company jobs retrieved",
    )


@router.post("", response_model=APIResponse[dict], summary="Create Job Posting")
def create_job_posting(
    data: CompanyJobCreateRequest,
    request: Request,
    user: Any = Depends(get_current_company_user),
    db: Session = Depends(get_db),
):
    result = create_job_controller(data, user, request, db)
    return success_response(data=result, message="Job posting created successfully")


@router.get("/{job_id}", response_model=APIResponse[dict], summary="Get Company Job Details")
def get_company_job(
    job_id: int,
    user: Any = Depends(get_current_company_user),
    db: Session = Depends(get_db),
):
    return success_response(data=get_job_controller(job_id, user, db))


@router.put("/{job_id}", response_model=APIResponse[dict], summary="Update Company Job")
def update_company_job(
    job_id: int,
    data: CompanyJobUpdateRequest,
    user: Any = Depends(get_current_company_user),
    db: Session = Depends(get_db),
):
    result = update_job_controller(job_id, data, user, db)
    return success_response(data=result, message="Job updated successfully")


@router.patch("/{job_id}/status", response_model=APIResponse[dict], summary="Toggle Job Status")
def toggle_job_status(
    job_id: int,
    status_val: str = Query(..., alias="status", pattern="^(?i)(published|draft|closed|paused|active)$"),
    user: Any = Depends(get_current_company_user),
    db: Session = Depends(get_db),
):
    norm_status = toggle_status_controller(job_id, status_val, user, db)
    return success_response(message=f"Job status updated to {norm_status}")


@router.post("/{job_id}/duplicate", response_model=APIResponse[dict], summary="Duplicate Job")
def duplicate_company_job(
    job_id: int,
    user: Any = Depends(get_current_company_user),
    db: Session = Depends(get_db),
):
    result = duplicate_job_controller(job_id, user, db)
    return success_response(data=result, message="Job duplicated successfully")


@router.delete("/{job_id}", response_model=APIResponse[None], summary="Delete Job")
def delete_company_job(
    job_id: int,
    user: Any = Depends(get_current_company_user),
    db: Session = Depends(get_db),
):
    delete_job_controller(job_id, user, db)
    return success_response(message="Job posting deleted successfully")
