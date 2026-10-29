# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/plans/service.py
# Purpose : Domain logic for Subscription Plans (VND Commercial Model & FSD Alignment)
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("admin_plans_service")

# Subscription Plans configuration aligned with FSD-003, FSD-005 & BRD LV-BP-801
SUBSCRIPTION_PLANS: List[Dict[str, Any]] = [
    {
        "id": "Freemium",
        "name": "Freemium",
        "tier": "Freemium",
        "price": "0 VND",
        "price_monthly": 0,
        "price_annual": 0,
        "posting_limit": 999,  # Phase 1 unlimited free postings per FSD-003 BR-002
        "retention_months": 6,  # FSD-005 BR-012 per-plan retention
        "ai_features": False,
        "blurb": "Phase 1 Early Access — Unlimited Free Postings",
        "features": [
            "Up to 3 active jobs (999 during Phase 1)",
            "Candidate pipeline management",
            "1 team member seat",
            "Standard company profile",
            "Email customer support",
        ],
        "active": True,
    },
    {
        "id": "Professional",
        "name": "Professional",
        "tier": "Professional",
        "price": "2,900,000 VND / mo",
        "price_monthly": 2900000,
        "price_annual": 2320000,
        "posting_limit": 25,
        "retention_months": 12,
        "ai_features": True,
        "blurb": "For growing companies and active talent acquisition teams",
        "features": [
            "Up to 25 active job postings",
            "AI candidate screening & fit scoring",
            "AI job description assistant",
            "Unlimited team members & roles",
            "Verified Employer badge",
            "Priority customer support",
        ],
        "active": True,
    },
    {
        "id": "Enterprise",
        "name": "Enterprise",
        "tier": "Enterprise",
        "price": "Custom",
        "price_monthly": None,
        "price_annual": None,
        "posting_limit": None,
        "retention_months": 36,
        "ai_features": True,
        "blurb": "For organizations with advanced recruitment requirements and high volume",
        "features": [
            "Unlimited active job postings",
            "Full AI suite & recruitment analytics",
            "SSO authentication & enterprise security",
            "Custom data exports & audit logs",
            "Dedicated 24/7 account manager & SLA",
        ],
        "active": True,
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

    if "name" in updates:
        plan["name"] = str(updates["name"])
    if "price" in updates:
        plan["price"] = str(updates["price"])
    if "price_monthly" in updates:
        plan["price_monthly"] = updates["price_monthly"]
    if "price_annual" in updates:
        plan["price_annual"] = updates["price_annual"]
    if "posting_limit" in updates:
        plan["posting_limit"] = updates["posting_limit"]
    elif "limits" in updates:
        plan["posting_limit"] = updates["limits"]
    if "retention_months" in updates:
        plan["retention_months"] = int(updates["retention_months"])
    if "ai_features" in updates:
        plan["ai_features"] = bool(updates["ai_features"])
    if "blurb" in updates:
        plan["blurb"] = str(updates["blurb"])
    if "features" in updates:
        plan["features"] = list(updates["features"])
    if "active" in updates:
        plan["active"] = bool(updates["active"])

    logger.info(f"Updated plan '{plan['id']}' with new configuration")
    return plan
