# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/templates/router.py
# Purpose : FastAPI router for Company Rejection Templates (EMP-FR-025b / e13)
# ─────────────────────────────────────────────────────────────────────────────

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import User
from shared.schemas import APIResponse
from shared.utils import get_current_company_user, success_response

from services.company_service.app.api.templates.schemas import (
    CompanyRejectionTemplateResponse,
    CreateRejectionTemplateRequest,
    UpdateRejectionTemplateRequest,
)
from services.company_service.app.api.templates.controller import (
    list_templates_controller,
    create_template_controller,
    update_template_controller,
    delete_template_controller,
)

router = APIRouter(prefix="/templates", tags=["Rejection Templates"])


@router.get("/rejection", response_model=APIResponse[List[CompanyRejectionTemplateResponse]], summary="List Rejection Templates")
def list_rejection_templates(
    user: User = Depends(get_current_company_user),
    db: Session = Depends(get_db),
):
    data = list_templates_controller(user=user, db=db)
    return success_response(data=data)


@router.post("/rejection", response_model=APIResponse[CompanyRejectionTemplateResponse], summary="Create Rejection Template")
def create_rejection_template(
    payload: CreateRejectionTemplateRequest,
    user: User = Depends(get_current_company_user),
    db: Session = Depends(get_db),
):
    data = create_template_controller(payload=payload, user=user, db=db)
    return success_response(data=data, message="Rejection template created successfully")


@router.put("/rejection/{template_id}", response_model=APIResponse[CompanyRejectionTemplateResponse], summary="Update Rejection Template")
def update_rejection_template(
    template_id: int,
    payload: UpdateRejectionTemplateRequest,
    user: User = Depends(get_current_company_user),
    db: Session = Depends(get_db),
):
    data = update_template_controller(template_id=template_id, payload=payload, user=user, db=db)
    return success_response(data=data, message="Rejection template updated successfully")


@router.delete("/rejection/{template_id}", response_model=APIResponse[dict], summary="Delete Rejection Template")
def delete_rejection_template(
    template_id: int,
    user: User = Depends(get_current_company_user),
    db: Session = Depends(get_db),
):
    delete_template_controller(template_id=template_id, user=user, db=db)
    return success_response(data={"deleted": True}, message="Rejection template deleted successfully")
