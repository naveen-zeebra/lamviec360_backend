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
from .schemas import CompanyVerifySchema, UpdateCompanyPlanSchema, CompanyAdminUpdateSchema
from .controller import (
    list_companies_controller,
    get_company_detail_controller,
    verify_company_controller,
    toggle_feature_company_controller,
    update_company_plan_controller,
    update_company_details_controller,
)

router = APIRouter(prefix="/companies", tags=["Admin Company Verification"])


@router.get("", response_model=PaginatedResponse[dict])
def list_companies(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=5000),
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
