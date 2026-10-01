# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/profile/router.py
# Purpose : Presentation layer (FastAPI endpoints) for Company Profile
# ─────────────────────────────────────────────────────────────────────────────

from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.schemas import APIResponse
from shared.utils import get_current_company_user, success_response

from .schemas import CompanyProfileUpdateSchema
from .controller import (
    get_company_profile_controller,
    update_company_profile_controller,
)

router = APIRouter(prefix="/profile", tags=["Company Profile"])


@router.get("", response_model=APIResponse[dict], summary="Get Company Profile")
def get_company_profile(
    user: Any = Depends(get_current_company_user),
    db: Session = Depends(get_db),
):
    return success_response(data=get_company_profile_controller(user, db))


@router.put("", response_model=APIResponse[dict], summary="Update Company Profile")
def update_company_profile(
    data: CompanyProfileUpdateSchema,
    user: Any = Depends(get_current_company_user),
    db: Session = Depends(get_db),
):
    return success_response(
        data=update_company_profile_controller(data, user, db),
        message="Company profile updated successfully",
    )
