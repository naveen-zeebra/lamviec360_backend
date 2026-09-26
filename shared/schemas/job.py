from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from shared.schemas.company import CompanyProfileOut

class JobPostingBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10)
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    job_type: str = "Full-time"
    workplace_type: str = "On-site"
    experience_level: Optional[str] = "Mid-level"
    city: Optional[str] = None
    country: str = "Vietnam"
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: str = "USD"
    is_negotiable: bool = False
    required_skills: Optional[str] = None

class JobPostingCreate(JobPostingBase):
    status: Optional[str] = "published"

class JobPostingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    job_type: Optional[str] = None
    workplace_type: Optional[str] = None
    experience_level: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    is_negotiable: Optional[bool] = None
    required_skills: Optional[str] = None
    status: Optional[str] = None

class JobPostingOut(JobPostingBase):
    id: int
    company_id: int
    status: str
    moderation_status: str
    views_count: int = 0
    applications_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    company: Optional[CompanyProfileOut] = None

    class Config:
        from_attributes = True

class JobFilterParams(BaseModel):
    keyword: Optional[str] = None
    city: Optional[str] = None
    job_type: Optional[str] = None
    workplace_type: Optional[str] = None
    experience_level: Optional[str] = None
    min_salary: Optional[float] = None
    skills: Optional[str] = None
    page: int = 1
    page_size: int = 10
