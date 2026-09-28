# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/plans/controller.py
# Purpose : Orchestration layer for Admin Subscription Plans
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session

from shared.models import User
from shared.utils import log_audit_event
from shared.utils.logger import get_logger
from .schemas import PlanUpdateRequest
from .service import (
    get_all_subscription_plans,
    get_plan_by_id,
    update_subscription_plan,
)

logger = get_logger("admin_plans_controller")


def list_plans_controller() -> List[Dict[str, Any]]:
    """Retrieve all configurable subscription plans."""
    return get_all_subscription_plans()


def update_plan_controller(
    db: Session,
    plan_id: str,
    data: PlanUpdateRequest,
    current_admin: User,
    request: Optional[Request] = None,
) -> Dict[str, Any]:
    """Update subscription plan pricing, limits, or features."""
    plan = get_plan_by_id(plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan '{plan_id}' not found",
        )

    updated = update_subscription_plan(plan_id, data.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan '{plan_id}' not found",
        )

    log_audit_event(
        db,
        action="UPDATE_PLAN",
        module="ADMIN_PLANS",
        description=f"Admin {current_admin.email} updated plan '{updated['id']}'",
        user_id=current_admin.id,
        user_email=current_admin.email,
        user_type=current_admin.user_type,
        request=request,
    )

    return updated
