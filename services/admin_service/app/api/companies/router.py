# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/companies/router.py
# Purpose : HTTP Routing endpoints for Admin Company Verification
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import User
from shared.schemas import PaginatedResponse, APIResponse
from shared.utils import require_roles, success_response, paginated_response
from .schemas import CompanyVerifySchema, UpdateCompanyPlanSchema
from .controller import (
    list_companies_controller,
    get_company_detail_controller,
    verify_company_controller,
    toggle_feature_company_controller,
    update_company_plan_controller,
)

router = APIRouter(prefix="/companies", tags=["Admin Company Verification"])


@router.get("", response_model=PaginatedResponse[dict])
def list_companies(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    """List companies with verification status filter and search query."""
    items, total_items = list_companies_controller(
        db=db,
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
        message="Companies retrieved",
    )


@router.get("/{company_id}", response_model=APIResponse[dict])
def get_company_detail(
    company_id: int,
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    """Retrieve full company profile information."""
    data = get_company_detail_controller(db=db, company_id=company_id)
    return success_response(data=data)


@router.patch("/{company_id}/verify", response_model=APIResponse[dict])
def verify_company(
    company_id: int,
    data: CompanyVerifySchema,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    """Update company verification status (verified, rejected, pending)."""
    res = verify_company_controller(
        db=db,
        company_id=company_id,
        data=data,
        current_admin=current_admin,
        request=request,
    )
    return success_response(
        data=res,
        message=f"Company verification set to {data.verification_status}",
    )


@router.patch("/{company_id}/feature", response_model=APIResponse[dict])
def toggle_feature_company(
    company_id: int,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    """Toggle whether a company is featured on the platform."""
    is_featured = toggle_feature_company_controller(
        db=db,
        company_id=company_id,
        current_admin=current_admin,
        request=request,
    )
    status_str = "featured" if is_featured else "unfeatured"
    return success_response(
        data={"is_featured": is_featured},
        message=f"Company {status_str}",
    )


@router.patch("/{company_id}/plan", response_model=APIResponse[dict])
def update_company_plan(
    company_id: int,
    data: UpdateCompanyPlanSchema,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
):
    """Update subscription plan assigned to a company."""
    res = update_company_plan_controller(
        db=db,
        company_id=company_id,
        data=data,
        current_admin=current_admin,
        request=request,
    )
    return success_response(
        data=res,
        message=f"Company plan updated to {data.plan_id}",
    )
