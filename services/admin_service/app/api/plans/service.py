# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/plans/service.py
# Purpose : Domain logic for Subscription Plans
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("admin_plans_service")

# Subscription Plans configuration
SUBSCRIPTION_PLANS: List[Dict[str, Any]] = [
    {
        "id": "Freemium",
        "price": 0.0,
        "limits": 3,
        "features": ["Basic Analytics", "Standard Support"],
    },
    {
        "id": "Professional",
        "price": 99.0,
        "limits": 25,
        "features": ["Advanced Analytics", "Priority Support"],
    },
    {
        "id": "Enterprise",
        "price": 499.0,
        "limits": None,
        "features": ["Custom Analytics", "24/7 Dedicated Support"],
    },
]


@service_error_handler
def get_all_subscription_plans() -> List[Dict[str, Any]]:
    """Retrieve available platform subscription plans."""
    return [dict(p) for p in SUBSCRIPTION_PLANS]


@service_error_handler
def get_plan_by_id(plan_id: str) -> Optional[Dict[str, Any]]:
    """Find a specific subscription plan by ID."""
    return next((p for p in SUBSCRIPTION_PLANS if p["id"].lower() == plan_id.lower()), None)


@service_error_handler
def update_subscription_plan(plan_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update settings on a subscription plan."""
    plan = get_plan_by_id(plan_id)
    if not plan:
        return None

    if updates.get("price") is not None:
        plan["price"] = float(updates["price"])
    if updates.get("limits") is not None:
        plan["limits"] = updates["limits"]
    if updates.get("features") is not None:
        plan["features"] = list(updates["features"])

    logger.info(f"Updated plan '{plan['id']}' with new configuration")
    return plan
