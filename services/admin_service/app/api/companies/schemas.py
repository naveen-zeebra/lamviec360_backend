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


class CompanyAdminUpdateSchema(BaseModel):
    company_name: Optional[str] = None
    name: Optional[str] = None
    legal_name: Optional[str] = None
    tax_code: Optional[str] = None
    reg_number: Optional[str] = None
    regNumber: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    size: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    about: Optional[str] = None
    description: Optional[str] = None
    tagline: Optional[str] = None
    contact_person: Optional[str] = None
    adminName: Optional[str] = None
    contact_email: Optional[str] = None
    adminEmail: Optional[str] = None
    contact_phone: Optional[str] = None
    adminPhone: Optional[str] = None
    benefits: Optional[str] = None
    is_featured: Optional[bool] = None
    is_public: Optional[bool] = None
    isPublic: Optional[bool] = None
    verification_status: Optional[str] = None

    class Config:
        extra = "allow"

