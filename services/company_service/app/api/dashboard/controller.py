# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/dashboard/controller.py
# Purpose : Orchestration layer for Company Dashboard
# ─────────────────────────────────────────────────────────────────────────────

from typing import Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from shared.models import User
from shared.utils.logger import get_logger

from . import service

logger = get_logger("company_dashboard_controller")


def get_dashboard_controller(user: User, db: Session) -> Dict[str, Any]:
    """Compile aggregated metrics, quotas, and recent activity for company dashboard."""
    profile = service.get_company_tenant(user)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted: No employer organization associated with this tenant account",
        )

    metrics = service.compute_dashboard_metrics(db, profile.id)
    quota = service.compute_quota_metrics(profile, metrics["total_jobs"])
    recent = service.get_recent_applications(db, profile.id, limit=5)

    return {
        "metrics": metrics,
        "quota": quota,
        "recent_applications": recent,
    }
