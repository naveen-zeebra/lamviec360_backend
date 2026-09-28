from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, EmailStr


class CompanyProfileUpdateSchema(BaseModel):
    name: Optional[str] = None
    company_name: Optional[str] = None
    legal_name: Optional[str] = None
    tax_code: Optional[str] = None
    reg_number: Optional[str] = None
    regNumber: Optional[str] = None
    email: Optional[EmailStr] = None
    contact_email: Optional[EmailStr] = None
    phone: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_person: Optional[str] = None
    founded_year: Optional[Union[int, str]] = None
    linkedin_url: Optional[str] = None
    facebook_url: Optional[str] = None
    benefits: Optional[str] = None
    logo: Optional[str] = None
    logo_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    company_size: Optional[str] = None
    about: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    plan: Optional[str] = None
    subscription_tier: Optional[str] = None
    settings: Optional[Union[Dict[str, Any], str]] = None

    class Config:
        extra = "allow"
