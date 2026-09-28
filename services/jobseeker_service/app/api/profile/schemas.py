from typing import Optional
from pydantic import BaseModel


class JobSeekerProfileUpdateSchema(BaseModel):
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

    class Config:
        extra = "allow"
