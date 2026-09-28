# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/profile/router.py
# Purpose : Presentation layer (FastAPI endpoints) for Company Profile
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import User
from shared.schemas import APIResponse
from shared.utils import require_user_type, success_response

from .schemas import CompanyProfileUpdateSchema
from .controller import (
    get_company_profile_controller,
    update_company_profile_controller,
)

router = APIRouter(prefix="/profile", tags=["Company Profile"])


@router.get("", response_model=APIResponse[dict], summary="Get Company Profile")
def get_company_profile(
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    return success_response(data=get_company_profile_controller(user, db))


@router.put("", response_model=APIResponse[dict], summary="Update Company Profile")
def update_company_profile(
    data: CompanyProfileUpdateSchema,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    return success_response(
        data=update_company_profile_controller(data, user, db),
        message="Company profile updated successfully",
    )
