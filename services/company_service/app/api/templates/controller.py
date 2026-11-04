# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/templates/controller.py
# Purpose : Controller layer for Company Rejection Templates (EMP-FR-025b / e13)
# ─────────────────────────────────────────────────────────────────────────────

from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException
from shared.models.user import User
from shared.models.company import CompanyProfile
from services.company_service.app.api.templates.schemas import (
    CompanyRejectionTemplateResponse,
    CreateRejectionTemplateRequest,
    UpdateRejectionTemplateRequest,
)
from services.company_service.app.api.templates import service


def _require_company(user: User, db: Session) -> CompanyProfile:
    company = db.query(CompanyProfile).filter(CompanyProfile.user_id == user.id).first()
    if not company:
        raise HTTPException(status_code=403, detail="Active company profile required.")
    return company


def list_templates_controller(user: User, db: Session) -> List[CompanyRejectionTemplateResponse]:
    company = _require_company(user, db)
    return service.list_company_templates(db=db, company_id=company.id)


def create_template_controller(
    payload: CreateRejectionTemplateRequest, user: User, db: Session
) -> CompanyRejectionTemplateResponse:
    company = _require_company(user, db)
    return service.create_company_template(db=db, company_id=company.id, payload=payload)


def update_template_controller(
    template_id: int, payload: UpdateRejectionTemplateRequest, user: User, db: Session
) -> CompanyRejectionTemplateResponse:
    company = _require_company(user, db)
    return service.update_company_template(
        db=db, company_id=company.id, template_id=template_id, payload=payload
    )


def delete_template_controller(template_id: int, user: User, db: Session) -> bool:
    company = _require_company(user, db)
    return service.delete_company_template(db=db, company_id=company.id, template_id=template_id)

