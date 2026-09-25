from typing import Optional, Union, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field

class CompanyProfileBase(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=255)
    legal_name: Optional[str] = None
    logo_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    about: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: str = "Vietnam"
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_person: Optional[str] = None
    tax_code: Optional[str] = None
    founded_year: Optional[int] = None
    linkedin_url: Optional[str] = None
    facebook_url: Optional[str] = None
    benefits: Optional[str] = None
    subscription_tier: Optional[str] = "Freemium"

class CompanyProfileCreate(CompanyProfileBase):
    pass

class CompanyProfileUpdate(BaseModel):
    company_name: Optional[str] = None
    name: Optional[str] = None
    legal_name: Optional[str] = None
    logo_url: Optional[str] = None
    logo: Optional[str] = None
    cover_image_url: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    size: Optional[str] = None
    about: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    contact_email: Optional[str] = None
    email: Optional[str] = None
    contact_phone: Optional[str] = None
    phone: Optional[str] = None
    contact_person: Optional[str] = None
    tax_code: Optional[str] = None
    reg_number: Optional[str] = None
    regNumber: Optional[str] = None
    founded_year: Optional[Union[int, str]] = None
    linkedin_url: Optional[str] = None
    facebook_url: Optional[str] = None
    benefits: Optional[str] = None
    subscription_tier: Optional[str] = None
    plan: Optional[str] = None
    settings: Optional[Union[Dict[str, Any], str]] = None

class CompanyVerifyRequest(BaseModel):
    verification_status: str = Field(..., description="pending, verified, rejected")
    verification_notes: Optional[str] = None
    is_featured: Optional[bool] = None

class CompanyProfileOut(CompanyProfileBase):
    id: int
    user_id: int
    verification_status: str
    verification_notes: Optional[str] = None
    is_featured: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
