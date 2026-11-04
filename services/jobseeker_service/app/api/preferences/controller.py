# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/preferences/controller.py
# Purpose : Controller layer for Job Seeker notification & language preferences
# ─────────────────────────────────────────────────────────────────────────────

from sqlalchemy.orm import Session
from shared.models.user import User
from services.jobseeker_service.app.api.preferences.schemas import (
    SeekerPreferencesResponse,
    UpdateSeekerPreferencesRequest,
)
from services.jobseeker_service.app.api.preferences import service


def get_preferences_controller(user: User, db: Session) -> SeekerPreferencesResponse:
    return service.get_seeker_preferences(db=db, user=user)


def update_preferences_controller(
    payload: UpdateSeekerPreferencesRequest, user: User, db: Session
) -> SeekerPreferencesResponse:
    return service.update_seeker_preferences(db=db, user=user, payload=payload)

