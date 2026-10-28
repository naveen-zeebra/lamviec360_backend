# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/companies/schemas.py
# Purpose : Data transfer schemas for public Company Discovery & Showcase
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class CultureValueItem(BaseModel):
    title: str
    description: str
    icon: Optional[str] = "star"


class PublicCompanyListItem(BaseModel):
    id: int
    name: str
    company_name: str
    legal_name: Optional[str] = None
    logo_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    tagline: Optional[str] = None
    industry: Optional[str] = "Technology"
    company_size: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = "Vietnam"
    website: Optional[str] = None
    verified: bool = True
    is_featured: bool = False
    open_jobs_count: int = 0
    about: Optional[str] = None


class PublicCompanyDetail(BaseModel):
    id: int
    name: str
    company_name: str
    legal_name: Optional[str] = None
    logo_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    tagline: Optional[str] = None
    industry: Optional[str] = "Technology"
    company_size: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = "Vietnam"
    address: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_person: Optional[str] = None
    founded_year: Optional[int] = None
    linkedin_url: Optional[str] = None
    facebook_url: Optional[str] = None
    about: Optional[str] = None
    benefits: Optional[str] = None
    verified: bool = True
    is_featured: bool = False
    is_public: bool = True
    
    # Extended culture & work attributes
    workplace_model: Optional[str] = "Hybrid"  # Hybrid, On-site, Remote-friendly
    working_hours: Optional[str] = None
    culture_values: List[Dict[str, Any]] = []
    
    # Live open jobs
    open_jobs: List[Dict[str, Any]] = []
    open_jobs_count: int = 0
