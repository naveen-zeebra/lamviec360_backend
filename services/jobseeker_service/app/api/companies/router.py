# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/companies/router.py
# Purpose : HTTP Endpoints for public Company Discovery & Showcase
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.schemas import PaginatedResponse, APIResponse
from shared.utils import paginated_response, success_response

from .schemas import PublicCompanyListItem, PublicCompanyDetail
from .controller import (
    list_public_companies_controller,
    get_public_company_detail_controller,
)

router = APIRouter(prefix="/companies", tags=["Company Discovery & Showcase"])


@router.get("", response_model=PaginatedResponse[dict], summary="List Public Companies")
def list_public_companies(
    search: Optional[str] = Query(None, description="Search company name, tagline or description"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    city: Optional[str] = Query(None, description="Filter by city / location"),
    verified_only: bool = Query(False, description="Filter only verified companies"),
    featured_only: bool = Query(False, description="Filter only featured companies"),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Retrieve public verified companies directory with active open job counts."""
    items, total_items = list_public_companies_controller(
        db=db,
        search=search,
        industry=industry,
        city=city,
        verified_only=verified_only,
        featured_only=featured_only,
        page=page,
        page_size=page_size,
    )
    return paginated_response(
        items=items,
        total_items=total_items,
        page=page,
        page_size=page_size,
        message="Companies retrieved successfully",
    )


@router.get("/{id_or_slug}", response_model=APIResponse[dict], summary="Get Public Company Showcase Profile")
def get_public_company_detail(
    id_or_slug: str,
    db: Session = Depends(get_db),
):
    """Retrieve full company public branding, culture pillars, perks, and active live job openings."""
    data = get_public_company_detail_controller(db=db, id_or_slug=id_or_slug)
    return success_response(data=data)
