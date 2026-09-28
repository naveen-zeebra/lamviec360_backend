from typing import Optional, List
from pydantic import BaseModel, Field


class CompanyJobCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: str
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    job_type: str = "full_time"
    workplace_type: str = "on_site"
    experience_level: str = "mid"
    city: Optional[str] = None
    country: Optional[str] = "Vietnam"
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = "VND"
    is_negotiable: bool = False
    required_skills: Optional[str] = None
    status: Optional[str] = "published"


class CompanyJobUpdateRequest(BaseModel):
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
