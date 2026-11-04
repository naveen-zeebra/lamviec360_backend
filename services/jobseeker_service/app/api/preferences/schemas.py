# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/preferences/schemas.py
# Purpose : Pydantic schemas for Job Seeker notification & language preferences
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional
from pydantic import BaseModel, Field


class SeekerNotificationToggles(BaseModel):
    job_recommendations: bool = True
    application_updates: bool = True
    interview_alerts: bool = True
    marketing: bool = False
    in_app_enabled: bool = True


class SeekerPreferencesResponse(BaseModel):
    preferred_language: str = "vi"  # "vi" or "en"
    notifications: SeekerNotificationToggles


class UpdateSeekerPreferencesRequest(BaseModel):
    preferred_language: Optional[str] = Field(None, description="'vi' (primary) or 'en' (secondary)")
    job_recommendations: Optional[bool] = None
    application_updates: Optional[bool] = None
    interview_alerts: Optional[bool] = None
    marketing: Optional[bool] = None
    in_app_enabled: Optional[bool] = None

