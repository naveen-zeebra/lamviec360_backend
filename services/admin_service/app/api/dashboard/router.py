# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/dashboard/router.py
# Purpose : Presentation layer (FastAPI endpoints) for Admin Dashboard
# ─────────────────────────────────────────────────────────────────────────────

from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.schemas import APIResponse
from shared.utils import require_roles, success_response

from .controller import (
    get_dashboard_summary_controller,
    get_growth_metrics_controller,
    get_recent_activities_controller,
)

router = APIRouter(prefix="/dashboard", tags=["Admin Dashboard"])


@router.get("/summary", response_model=APIResponse[dict], summary="Get Dashboard Summary")
def get_dashboard_summary(
    user: Any = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    return success_response(data=get_dashboard_summary_controller(db))


@router.get("/growth", response_model=APIResponse[dict], summary="Get Growth Metrics")
def get_growth_metrics(
    user: Any = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    return success_response(data=get_growth_metrics_controller())


@router.get("/activities", response_model=APIResponse[list], summary="Get Recent Activities")
def get_recent_activities(
    user: Any = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    return success_response(data=get_recent_activities_controller(db))
