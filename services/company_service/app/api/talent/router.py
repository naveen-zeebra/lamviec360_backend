# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/talent/router.py
# Purpose : HTTP Endpoints for EMP-FR-030 Talent Search & EMP-FR-031 Access Control
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, Any
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.schemas import APIResponse
from shared.utils import success_response
from ..team.roles import require_company_permission
from .schemas import (
    TalentSearchFilterParams,
    TalentInvitationCreate,
)
from .controller import (
    search_talent_controller,
    get_talent_profile_controller,
    invite_talent_controller,
)

router = APIRouter(prefix="/talent", tags=["Talent Search & Discovery"])


@router.get("/search", response_model=APIResponse[dict], summary="Search Talent Profiles")
def search_talent(
    request: Request,
    keyword: Optional[str] = Query(None, description="Search keyword in name, headline, bio, skills"),
    skills: Optional[str] = Query(None, description="Comma-separated skills to filter"),
    job_title: Optional[str] = Query(None, description="Job title / headline filter"),
    location: Optional[str] = Query(None, description="Province / City location filter"),
    min_experience: Optional[float] = Query(None, ge=0, description="Minimum experience years"),
    max_experience: Optional[float] = Query(None, ge=0, description="Maximum experience years"),
    education_level: Optional[str] = Query(None, description="Education level"),
    min_salary: Optional[float] = Query(None, ge=0, description="Minimum salary in VND"),
    max_salary: Optional[float] = Query(None, ge=0, description="Maximum salary in VND"),
    availability: Optional[str] = Query(None, description="open_to_work or open_to_opportunities"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: Any = Depends(require_company_permission("talent.search")),
    db: Session = Depends(get_db),
):
    """
    EMP-FR-030: Search active Job Seeker talent profiles visible to employers.
    EMP-FR-031: Restricted to active/verified companies; Viewer role is forbidden.
    Excludes candidates marked 'Not looking' per JSP-FR-015.
    Masks contact details per BR-014.
    """
    filters = TalentSearchFilterParams(
        keyword=keyword,
        skills=skills,
        job_title=job_title,
        location=location,
        min_experience=min_experience,
        max_experience=max_experience,
        education_level=education_level,
        min_salary=min_salary,
        max_salary=max_salary,
        availability=availability,
        page=page,
        page_size=page_size,
    )
    res = search_talent_controller(db=db, current_user=user, filters=filters, request=request)
    return success_response(data=res, message="Talent profiles retrieved successfully")


@router.get("/{profile_id}", response_model=APIResponse[dict], summary="Get Talent Profile Detail")
def get_talent_profile(
    profile_id: int,
    request: Request,
    user: Any = Depends(require_company_permission("talent.search")),
    db: Session = Depends(get_db),
):
    """
    EMP-FR-021 & EMP-FR-030: Full candidate profile view.
    Contact details remain locked until approved per BR-014.
    """
    res = get_talent_profile_controller(db=db, current_user=user, profile_id=profile_id, request=request)
    return success_response(data=res, message="Talent profile retrieved successfully")


@router.post("/{profile_id}/invite", response_model=APIResponse[dict], summary="Invite Candidate to Job")
def invite_candidate(
    profile_id: int,
    payload: TalentInvitationCreate,
    request: Request,
    user: Any = Depends(require_company_permission("talent.search")),
    db: Session = Depends(get_db),
):
    """
    EMP-FR-030: Recruiter sends an invitation / contact request to a passive candidate.
    Dispatches notification to jobseeker.
    """
    res = invite_talent_controller(
        db=db,
        current_user=user,
        profile_id=profile_id,
        payload=payload,
        request=request,
    )
    return success_response(data=res, message=res.get("message", "Invitation sent successfully"))

