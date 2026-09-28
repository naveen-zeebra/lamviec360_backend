# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/data_retention/controller.py
# Purpose : Orchestration layer for Company Data Retention
# ─────────────────────────────────────────────────────────────────────────────

from typing import Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from shared.models import User
from shared.utils.logger import get_logger

from . import service

logger = get_logger("company_data_retention_controller")


def purge_company_data_controller(months: int, user: User, db: Session) -> Dict[str, Any]:
    """Execute candidate data purge according to tenant policy."""
    profile = service.get_company_tenant(user)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted: No employer organization associated with this tenant account",
        )

    deleted_count = service.purge_expired_company_applications(db, profile.id, months)
    return {
        "purged_count": deleted_count,
        "message": f"Purged {deleted_count} candidate records older than {months} months for company {profile.company_name}.",
    }
