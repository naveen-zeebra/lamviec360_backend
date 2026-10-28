from typing import Optional, List, Any
from pydantic import BaseModel, Field


class CompanyJobCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: str
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    department: Optional[str] = None
    job_type: Optional[str] = "Full-time"
    type: Optional[str] = None
    workplace_type: Optional[str] = "On-site"
    experience_level: Optional[str] = "Mid-level"
    experience: Optional[str] = None
    city: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = "Vietnam"
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salaryMin: Optional[float] = None
    salaryMax: Optional[float] = None
    salary_currency: Optional[str] = "VND"
    is_negotiable: Optional[bool] = False
    negotiable: Optional[bool] = None
    required_skills: Optional[str] = None
    skills: Optional[Any] = None
    education: Optional[str] = None
    vacancies: Optional[int] = 1
    deadline: Optional[str] = None
    expires_at: Optional[Any] = None
    documents: Optional[Any] = None
    status: Optional[str] = "published"
    ai_generated: Optional[bool] = False
    salary_type: Optional[str] = "Gross"
    salaryType: Optional[str] = None
    attitude_type: Optional[str] = None
    attitudeType: Optional[str] = None
    social_type: Optional[str] = None
    socialType: Optional[str] = None
    personality_type: Optional[str] = None
    personalityType: Optional[str] = None
    overtime_willingness: Optional[str] = None
    overtimeWillingness: Optional[str] = None
    project_work_reqs: Optional[str] = None
    projectWorkReqs: Optional[str] = None


class CompanyJobUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    department: Optional[str] = None
    job_type: Optional[str] = None
    type: Optional[str] = None
    workplace_type: Optional[str] = None
    experience_level: Optional[str] = None
    experience: Optional[str] = None
    city: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salaryMin: Optional[float] = None
    salaryMax: Optional[float] = None
    salary_currency: Optional[str] = None
    is_negotiable: Optional[bool] = None
    negotiable: Optional[bool] = None
    required_skills: Optional[str] = None
    skills: Optional[Any] = None
    education: Optional[str] = None
    vacancies: Optional[int] = None
    deadline: Optional[str] = None
    expires_at: Optional[Any] = None
    documents: Optional[Any] = None
    status: Optional[str] = None
    ai_generated: Optional[bool] = None
    salary_type: Optional[str] = None
    salaryType: Optional[str] = None
    attitude_type: Optional[str] = None
    attitudeType: Optional[str] = None
    social_type: Optional[str] = None
    socialType: Optional[str] = None
    personality_type: Optional[str] = None
    personalityType: Optional[str] = None
    overtime_willingness: Optional[str] = None
    overtimeWillingness: Optional[str] = None
    project_work_reqs: Optional[str] = None
    projectWorkReqs: Optional[str] = None
