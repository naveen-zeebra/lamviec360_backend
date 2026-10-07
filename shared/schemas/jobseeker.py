from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class JobSeekerProfileBase(BaseModel):
    headline: Optional[str] = None
    bio: Optional[str] = None
    resume_url: Optional[str] = None
    skills: Optional[str] = None
    experience_years: float = 0.0
    expected_salary: Optional[float] = None
    city: Optional[str] = None
    country: str = "Vietnam"
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    # BR-101-07 / BR-101-08
    is_visible: bool = True
    visibility: str = "public"
    is_archived: bool = False
    archived_at: Optional[datetime] = None
    archive_reason: Optional[str] = None

class JobSeekerProfileCreate(JobSeekerProfileBase):
    pass

class JobSeekerProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    headline: Optional[str] = None
    bio: Optional[str] = None
    resume_url: Optional[str] = None
    skills: Optional[str] = None
    experience_years: Optional[float] = None
    expected_salary: Optional[float] = None
    city: Optional[str] = None
    country: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    is_visible: Optional[bool] = None
    visibility: Optional[str] = None

class JobSeekerProfileOut(JobSeekerProfileBase):
    id: int
    user_id: int
    completeness: Optional[int] = None
    can_apply: Optional[bool] = None
    has_verified_contact: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class SavedJobOut(BaseModel):
    id: int
    job_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
