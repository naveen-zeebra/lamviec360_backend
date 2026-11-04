# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/preferences/router.py
# Purpose : FastAPI router for Job Seeker notification & language preferences
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import User
from shared.schemas import APIResponse
from shared.utils import get_current_jobseeker, success_response

from services.jobseeker_service.app.api.preferences.schemas import (
    SeekerPreferencesResponse,
    UpdateSeekerPreferencesRequest,
)
from services.jobseeker_service.app.api.preferences.controller import (
    get_preferences_controller,
    update_preferences_controller,
)

router = APIRouter(prefix="/preferences", tags=["Preferences"])


@router.get("", response_model=APIResponse[SeekerPreferencesResponse], summary="Get Notification Preferences & Language")
def get_preferences(
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    data = get_preferences_controller(user=user, db=db)
    return success_response(data=data)


@router.put("", response_model=APIResponse[SeekerPreferencesResponse], summary="Update Notification Preferences & Language")
def update_preferences(
    payload: UpdateSeekerPreferencesRequest,
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    data = update_preferences_controller(payload=payload, user=user, db=db)
    return success_response(data=data, message="Notification preferences updated successfully")

