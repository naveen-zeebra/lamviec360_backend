# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/talent/schemas.py
# Purpose : Pydantic schemas for EMP-FR-030 Talent Search & Discovery
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TalentSearchFilterParams(BaseModel):
    """EMP-FR-030 Filter parameters for searching Job Seeker talent profiles."""
    keyword: Optional[str] = Field(default=None, description="Search keyword in name, headline, bio, skills")
    skills: Optional[str] = Field(default=None, description="Comma-separated skills to filter by")
    job_title: Optional[str] = Field(default=None, description="Job title / headline filter")
    location: Optional[str] = Field(default=None, description="Province / City location filter")
    min_experience: Optional[float] = Field(default=None, ge=0, description="Minimum years of experience")
    max_experience: Optional[float] = Field(default=None, ge=0, description="Maximum years of experience")
    education_level: Optional[str] = Field(default=None, description="Highest education level")
    min_salary: Optional[float] = Field(default=None, ge=0, description="Minimum desired salary in VND")
    max_salary: Optional[float] = Field(default=None, ge=0, description="Maximum desired salary in VND")
    availability: Optional[str] = Field(default=None, description="open_to_work or open_to_opportunities")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class TalentCardResponse(BaseModel):
    """Compact candidate card representation for EMP-FR-030 search results."""
    id: int
    user_id: int
    full_name: str
    avatar_url: Optional[str] = None
    headline: Optional[str] = None
    bio: Optional[str] = None
    experience_years: float = 0.0
    expected_salary: Optional[float] = None
    city: Optional[str] = None
    country: str = "Vietnam"
    skills: List[str] = []
    job_availability: str = "open_to_work"  # open_to_work, open_to_opportunities
    education_level: Optional[str] = None
    allow_direct_message: bool = False  # JSP-FR-015
    contact_approved: bool = False       # BR-014
    contact_email: Optional[str] = None  # Masked if contact_approved is False
    contact_phone: Optional[str] = None  # Masked if contact_approved is False


class TalentProfileDetailResponse(BaseModel):
    """Full candidate profile view as defined in EMP-FR-021 & EMP-FR-030."""
    id: int
    user_id: int
    full_name: str
    avatar_url: Optional[str] = None
    headline: Optional[str] = None
    bio: Optional[str] = None
    experience_years: float = 0.0
    expected_salary: Optional[float] = None
    city: Optional[str] = None
    country: str = "Vietnam"
    skills: List[str] = []
    job_availability: str = "open_to_work"
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    education: List[Dict[str, Any]] = []
    experience: List[Dict[str, Any]] = []
    resume_url: Optional[str] = None
    allow_direct_message: bool = False
    contact_approved: bool = False
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None


class TalentInvitationCreate(BaseModel):
    """Recruiter invitation payload to reach out to a passive candidate."""
    job_id: int = Field(..., description="ID of open job posting for the invitation")
    message: Optional[str] = Field(default=None, description="Personalized recruiter message / note")

