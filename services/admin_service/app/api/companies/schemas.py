# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/companies/schemas.py
# Purpose : Schemas for Admin Company Management & Verification
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional
from pydantic import BaseModel, Field


class CompanyVerifySchema(BaseModel):
    verification_status: str = Field(..., description="verified | rejected | pending")
    verification_notes: Optional[str] = None
    is_featured: Optional[bool] = None


class UpdateCompanyPlanSchema(BaseModel):
    plan_id: str = Field(..., min_length=1)
