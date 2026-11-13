# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/jobs/schemas.py
# Purpose : Schemas for Admin Job Moderation
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional
from pydantic import BaseModel, Field


class JobModerationSchema(BaseModel):
    moderation_status: str = Field(..., description="verified | suspicious | approved | rejected | flagged | pending")
    moderation_notes: Optional[str] = None


class JobContentUpdateSchema(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    moderation_notes: Optional[str] = None
