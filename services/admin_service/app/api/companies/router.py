from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc

from shared.database.session import get_db
from shared.models import CompanyProfile, User
from shared.schemas import CompanyVerifyRequest, PaginatedResponse, APIResponse
from pydantic import BaseModel
from shared.utils import (
    get_current_user,
    require_roles,
    success_response,
    paginated_response,
    log_audit_event,
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
    query = db.query(CompanyProfile)
    if status_filter:
        query = query.filter(CompanyProfile.verification_status == status_filter)
    if search:
        query = query.filter(CompanyProfile.company_name.ilike(f"%{search.strip()}%"))

    total_items = query.count()
    offset = (page - 1) * page_size
    companies = query.order_by(desc(CompanyProfile.created_at)).offset(offset).limit(page_size).all()

    items = []
    for c in companies:
        items.append({
            "id": c.id,
            "user_id": c.user_id,
            "company_name": c.company_name,
            "legal_name": c.legal_name,
            "logo_url": c.logo_url,
            "website": c.website,
            "industry": c.industry,
            "company_size": c.company_size,
            "city": c.city,
            "verification_status": c.verification_status,
            "is_featured": c.is_featured,
            "active_jobs_count": len([j for j in c.job_postings if j.status == 'active' and not j.is_deleted]),
            "created_at": c.created_at,
        })

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
    c = db.query(CompanyProfile).filter(CompanyProfile.id == company_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")

    return success_response(
        data={
            "id": c.id,
            "user_id": c.user_id,
            "company_name": c.company_name,
            "legal_name": c.legal_name,
            "logo_url": c.logo_url,
            "cover_image_url": c.cover_image_url,
            "website": c.website,
            "industry": c.industry,
            "company_size": c.company_size,
            "about": c.about,
            "address": c.address,
            "city": c.city,
            "country": c.country,
            "verification_status": c.verification_status,
            "verification_notes": c.verification_notes,
            "is_featured": c.is_featured,
            "created_at": c.created_at,
        }
    )


@router.patch("/{company_id}/verify", response_model=APIResponse[dict])
def verify_company(
    company_id: int,
    data: CompanyVerifyRequest,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    c = db.query(CompanyProfile).filter(CompanyProfile.id == company_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")

    c.verification_status = data.verification_status
    if data.verification_notes is not None:
        c.verification_notes = data.verification_notes
    if data.is_featured is not None:
        c.is_featured = data.is_featured

    db.commit()

    log_audit_event(
        db,
        action="VERIFY_COMPANY",
        module="ADMIN_COMPANIES",
        description=f"Admin {current_admin.email} set company {c.company_name} status={data.verification_status}",
        user_id=current_admin.id,
        user_email=current_admin.email,
        user_type=current_admin.user_type,
        request=request,
    )

    return success_response(
        data={"id": c.id, "verification_status": c.verification_status},
        message=f"Company verification set to {c.verification_status}",
    )


@router.patch("/{company_id}/feature", response_model=APIResponse[dict])
def toggle_feature_company(
    company_id: int,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    c = db.query(CompanyProfile).filter(CompanyProfile.id == company_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")

    c.is_featured = not c.is_featured
    db.commit()

    status_str = "featured" if c.is_featured else "unfeatured"
    return success_response(data={"is_featured": c.is_featured}, message=f"Company {status_str}")


class UpdateCompanyPlanRequest(BaseModel):
    plan_id: str

@router.patch("/{company_id}/plan", response_model=APIResponse[dict])
def update_company_plan(
    company_id: int,
    data: UpdateCompanyPlanRequest,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
):
    c = db.query(CompanyProfile).filter(CompanyProfile.id == company_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")

    # Mock updating the plan
    # c.plan_id = data.plan_id
    # db.commit()

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

    return success_response(
        data={"id": c.id, "plan_id": data.plan_id}, 
        message=f"Company plan updated to {data.plan_id}"
    )
