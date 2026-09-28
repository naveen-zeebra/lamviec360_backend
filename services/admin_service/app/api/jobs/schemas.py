# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/jobs/schemas.py
# Purpose : Schemas for Admin Job Moderation
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional
from pydantic import BaseModel, Field


class JobModerationSchema(BaseModel):
    moderation_status: str = Field(..., description="approved | rejected | pending")
    moderation_notes: Optional[str] = None
