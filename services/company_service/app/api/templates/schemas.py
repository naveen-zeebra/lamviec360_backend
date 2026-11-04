# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/templates/schemas.py
# Purpose : Schemas for Company Rejection Templates (EMP-FR-025b / e13)
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional
from pydantic import BaseModel, Field


class CompanyRejectionTemplateResponse(BaseModel):
    id: int
    company_id: int
    title: str
    reason_code: str
    subject: str
    body_text: str
    language: str = "vi"
    is_default: bool = False
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class CreateRejectionTemplateRequest(BaseModel):
    title: str = Field(..., max_length=255)
    reason_code: Optional[str] = "qualifications"
    subject: str = Field(..., max_length=255)
    body_text: str
    language: Optional[str] = "vi"
    is_default: Optional[bool] = False


class UpdateRejectionTemplateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    reason_code: Optional[str] = None
    subject: Optional[str] = Field(None, max_length=255)
    body_text: Optional[str] = None
    language: Optional[str] = None
    is_default: Optional[bool] = None

