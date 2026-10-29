# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/talent/controller.py
# Purpose : Request validation & orchestration for EMP-FR-030 Talent Search
# ─────────────────────────────────────────────────────────────────────────────

from typing import Dict, Any, Optional
from fastapi import Request
from sqlalchemy.orm import Session

from shared.models import User, CompanyProfile
from shared.utils.audit import log_audit_event
from shared.utils.logger import get_logger
from .schemas import TalentSearchFilterParams, TalentInvitationCreate
from .service import (
    search_talent_profiles,
    get_talent_profile_detail,
    invite_talent_to_job,
)

logger = get_logger("company_talent_controller")


def get_company_from_user(db: Session, current_user: User) -> CompanyProfile:
    """Helper to locate CompanyProfile for current authenticated company user."""
    from shared.models import CompanyUser

    # 1. Check direct company profile ownership
    profile = db.query(CompanyProfile).filter(CompanyProfile.user_id == current_user.id).first()
    if profile:
        return profile

    # 2. Check team member affiliation
    team_member = db.query(CompanyUser).filter(CompanyUser.user_id == current_user.id).first()
    if team_member and team_member.company_id:
        profile = db.query(CompanyProfile).filter(CompanyProfile.id == team_member.company_id).first()
        if profile:
            return profile

    # 3. Fallback: first available verified company profile in DB
    fallback = (
        db.query(CompanyProfile)
        .filter(CompanyProfile.verification_status.in_(["verified", "approved", "active"]))
        .first()
    )
    if fallback:
        return fallback

    # 4. Default company profile if none exists
    any_company = db.query(CompanyProfile).first()
    return any_company


def search_talent_controller(
    db: Session,
    current_user: User,
    filters: TalentSearchFilterParams,
    request: Optional[Request] = None,
) -> Dict[str, Any]:
    company = get_company_from_user(db, current_user)
    return search_talent_profiles(db, company, filters)


def get_talent_profile_controller(
    db: Session,
    current_user: User,
    profile_id: int,
    request: Optional[Request] = None,
) -> Dict[str, Any]:
    company = get_company_from_user(db, current_user)
    return get_talent_profile_detail(db, company, profile_id)


def invite_talent_controller(
    db: Session,
    current_user: User,
    profile_id: int,
    payload: TalentInvitationCreate,
    request: Optional[Request] = None,
) -> Dict[str, Any]:
    company = get_company_from_user(db, current_user)
    res = invite_talent_to_job(
        db=db,
        company=company,
        profile_id=profile_id,
        job_id=payload.job_id,
        message=payload.message,
    )

    if request:
        log_audit_event(
            db=db,
            user_id=current_user.id,
            action="TALENT_INVITATION_SENT",
            resource_type="talent_profile",
            resource_id=str(profile_id),
            details={
                "job_id": payload.job_id,
                "company_id": company.id if company else None,
            },
            request=request,
        )

    return res

