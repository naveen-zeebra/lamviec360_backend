# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/dashboard/router.py
# Purpose : Presentation layer (FastAPI endpoints) for Company Dashboard
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import User
from shared.schemas import APIResponse
from shared.utils import require_user_type, success_response

from .schemas import CompanyDashboardResponseSchema
from .controller import get_dashboard_controller

router = APIRouter(prefix="/dashboard", tags=["Company Dashboard"])


@router.get("", response_model=APIResponse[dict], summary="Get Company Dashboard Data")
def get_company_dashboard(
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    return success_response(data=get_dashboard_controller(user, db))
