# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/plans/router.py
# Purpose : HTTP Routing endpoints for Subscription Plans
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import User
from shared.schemas import APIResponse
from shared.utils import require_roles, success_response
from .schemas import PlanUpdateRequest
from .controller import list_plans_controller, update_plan_controller

router = APIRouter(prefix="/plans", tags=["Admin Subscription Plans"])


@router.get("", response_model=APIResponse[list])
def list_plans(
    current_admin: User = Depends(require_roles("super_admin", "admin")),
):
    """Retrieve all available subscription plans and their limits."""
    plans = list_plans_controller()
    return success_response(data=plans, message="Subscription plans retrieved")


@router.put("/{plan_id}", response_model=APIResponse[dict])
def update_plan(
    plan_id: str,
    data: PlanUpdateRequest,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
):
    """Update price, limits, or features for a subscription plan."""
    updated = update_plan_controller(
        db=db,
        plan_id=plan_id,
        data=data,
        current_admin=current_admin,
        request=request,
    )
    return success_response(data=updated, message=f"Plan {updated['id']} updated successfully")
