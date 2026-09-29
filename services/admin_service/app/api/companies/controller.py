# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/companies/controller.py
# Purpose : Orchestration layer for Admin Company Verification & Management
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session

from shared.models import User
from shared.utils import log_audit_event
from shared.utils.logger import get_logger
from .schemas import CompanyVerifySchema, UpdateCompanyPlanSchema
from .service import (
    list_companies,
    get_company_by_id,
    update_company_verification,
    toggle_company_feature_status,
    serialize_company_detail,
)

logger = get_logger("admin_companies_controller")


def list_companies_controller(
    db: Session,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieve filtered and paginated companies."""
    return list_companies(
        db=db,
        status_filter=status_filter,
        search=search,
        page=page,
        page_size=page_size,
    )


def get_company_detail_controller(db: Session, company_id: int) -> Dict[str, Any]:
    """Retrieve full company details."""
    c = get_company_by_id(db, company_id)
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} not found",
        )
    return serialize_company_detail(c)


def verify_company_controller(
    db: Session,
    company_id: int,
    data: CompanyVerifySchema,
    current_admin: User,
    request: Optional[Request] = None,
) -> Dict[str, Any]:
    """Review and update verification status of a company."""
    c = get_company_by_id(db, company_id)
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} not found",
        )

    updated = update_company_verification(
        db=db,
        company=c,
        verification_status=data.verification_status,
        verification_notes=data.verification_notes,
        is_featured=data.is_featured,
    )

    log_audit_event(
        db,
        action="VERIFY_COMPANY",
        module="ADMIN_COMPANIES",
        description=f"Admin {current_admin.email} set company '{updated.company_name}' status={data.verification_status}",
        user_id=current_admin.id,
        user_email=current_admin.email,
        user_type=current_admin.user_type,
        request=request,
    )

    return {"id": updated.id, "verification_status": updated.verification_status}


def toggle_feature_company_controller(
    db: Session,
    company_id: int,
    current_admin: User,
    request: Optional[Request] = None,
) -> bool:
    """Toggle is_featured flag for a company."""
    c = get_company_by_id(db, company_id)
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} not found",
        )

    new_status = toggle_company_feature_status(db, c)
    status_label = "FEATURE_COMPANY" if new_status else "UNFEATURE_COMPANY"

    log_audit_event(
        db,
        action=status_label,
        module="ADMIN_COMPANIES",
        description=f"Admin {current_admin.email} set featured={new_status} on company '{c.company_name}'",
        user_id=current_admin.id,
        user_email=current_admin.email,
        user_type=current_admin.user_type,
        request=request,
    )

    return new_status


def update_company_plan_controller(
    db: Session,
    company_id: int,
    data: UpdateCompanyPlanSchema,
    current_admin: User,
    request: Optional[Request] = None,
) -> Dict[str, Any]:
    """Update subscription plan assigned to a company."""
    c = get_company_by_id(db, company_id)
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} not found",
        )

    c.subscription_tier = data.plan_id
    db.commit()
    db.refresh(c)

    log_audit_event(
        db,
        action="UPDATE_COMPANY_PLAN",
        module="ADMIN_COMPANIES",
        description=f"Admin {current_admin.email} updated company '{c.company_name}' plan to {data.plan_id}",
        user_id=current_admin.id,
        user_email=current_admin.email,
        user_type=current_admin.user_type,
        request=request,
    )

    return {"id": c.id, "plan_id": data.plan_id}
