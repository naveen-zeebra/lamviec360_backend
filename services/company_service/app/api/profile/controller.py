# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/profile/controller.py
# Purpose : Orchestration layer for Company Profile
# ─────────────────────────────────────────────────────────────────────────────

from typing import Dict, Any
from sqlalchemy.orm import Session
from shared.models import User
from shared.utils.logger import get_logger
from . import service
from .schemas import CompanyProfileUpdateSchema

logger = get_logger("company_profile_controller")


def get_company_profile_controller(user: User, db: Session) -> Dict[str, Any]:
    """Retrieve full company profile for authenticated company user."""
    profile = service.get_or_create_company_profile(db, user)
    return service.serialize_company_profile(profile, user)


def update_company_profile_controller(
    data: CompanyProfileUpdateSchema,
    user: User,
    db: Session,
) -> Dict[str, Any]:
    """Update profile and return refreshed profile dictionary."""
    profile = service.get_or_create_company_profile(db, user)
    data_dict = data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else data.dict(exclude_unset=True)
    updated_profile = service.update_company_profile_fields(db, profile, data_dict)
    return service.serialize_company_profile(updated_profile, user)
