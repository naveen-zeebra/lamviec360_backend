# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/companies/controller.py
# Purpose : Orchestration layer for public Company Discovery & Showcase
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from . import service


def list_public_companies_controller(
    db: Session,
    search: Optional[str] = None,
    industry: Optional[str] = None,
    city: Optional[str] = None,
    verified_only: bool = False,
    featured_only: bool = False,
    page: int = 1,
    page_size: int = 12,
) -> Tuple[List[Dict[str, Any]], int]:
    return service.list_public_companies(
        db=db,
        search=search,
        industry=industry,
        city=city,
        verified_only=verified_only,
        featured_only=featured_only,
        page=page,
        page_size=page_size,
    )


def get_public_company_detail_controller(
    db: Session,
    id_or_slug: str,
) -> Dict[str, Any]:
    company = service.get_public_company_by_id_or_slug(db, id_or_slug)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company '{id_or_slug}' not found",
        )
    return company
