# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/notifications/schemas.py
# Purpose : Pydantic schemas for Job Seeker Notifications
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional
from pydantic import BaseModel, Field


class NotificationItem(BaseModel):
    id: int
    title: str
    message: str
    type: str = "status"
    applicationId: Optional[int] = None
    application_id: Optional[int] = None
    read: bool = False
    date: str
    created_at: str

    class Config:
        from_attributes = True


class CreateNotificationRequest(BaseModel):
    title: str = Field(..., max_length=255)
    message: str
    type: Optional[str] = "status"
    application_id: Optional[int] = None
