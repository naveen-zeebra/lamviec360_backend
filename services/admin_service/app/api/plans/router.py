from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from shared.database.session import get_db
from shared.models import User
from shared.schemas import APIResponse
from shared.utils import get_current_user, require_roles, success_response, log_audit_event

router = APIRouter(prefix="/plans", tags=["Admin Subscription Plans"])

# Mock Plans Database
MOCK_PLANS = [
    {"id": "Freemium", "price": 0, "limits": 3, "features": ["Basic Analytics", "Standard Support"]},
    {"id": "Professional", "price": 99, "limits": 25, "features": ["Advanced Analytics", "Priority Support"]},
    {"id": "Enterprise", "price": 499, "limits": None, "features": ["Custom Analytics", "24/7 Dedicated Support"]}
]

class PlanUpdateRequest(BaseModel):
    price: Optional[float] = None
    limits: Optional[int] = None
    features: Optional[list[str]] = None

@router.get("", response_model=APIResponse[list])
def list_plans(
    current_admin: User = Depends(require_roles("super_admin", "admin")),
):
    return success_response(data=MOCK_PLANS, message="Subscription plans retrieved")

@router.put("/{plan_id}", response_model=APIResponse[dict])
def update_plan(
    plan_id: str,
    data: PlanUpdateRequest,
    request: Request,
    current_admin: User = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
):
    plan = next((p for p in MOCK_PLANS if p["id"].lower() == plan_id.lower()), None)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    if data.price is not None:
        plan["price"] = data.price
    if data.limits is not None:
        plan["limits"] = data.limits
    if data.features is not None:
        plan["features"] = data.features
        
    log_audit_event(
        db,
        action="UPDATE_PLAN",
        module="ADMIN_PLANS",
        description=f"Admin {current_admin.email} updated plan '{plan['id']}'",
        user_id=current_admin.id,
        user_email=current_admin.email,
        user_type=current_admin.user_type,
        request=request,
    )
    
    return success_response(data=plan, message=f"Plan {plan['id']} updated successfully")
