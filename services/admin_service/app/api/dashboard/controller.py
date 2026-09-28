# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/dashboard/controller.py
# Purpose : Orchestration layer for Platform Admin Dashboard
# ─────────────────────────────────────────────────────────────────────────────

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from shared.utils.logger import get_logger
from . import service

logger = get_logger("admin_dashboard_controller")


def get_dashboard_summary_controller(db: Session) -> Dict[str, Any]:
    """Retrieve platform aggregate statistics."""
    return service.compute_dashboard_summary(db)


def get_growth_metrics_controller() -> Dict[str, Any]:
    """Retrieve monthly growth statistics."""
    return service.get_growth_metrics_data()


def get_recent_activities_controller(db: Session) -> List[Dict[str, Any]]:
    """Retrieve recent platform audit entries."""
    return service.get_recent_audit_activities(db, limit=10)
