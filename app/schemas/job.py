from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class JobCreate(BaseModel):
    title: str
    department: Optional[str] = ""
    type: str = "Full-time"
    location: str = "Ho Chi Minh City"
    salary_min: Optional[str] = None
    salary_max: Optional[str] = None
    negotiable: bool = False
    jd: str
    skills: List[str] = []
    experience: Optional[str] = ""
    education: Optional[str] = ""
    deadline: Optional[datetime] = None
    vacancies: int = 1
    documents: List[str] = ["CV / Resume"]
    status: str = "Draft"
    ai_generated: bool = False


class JobUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    type: Optional[str] = None
    location: Optional[str] = None
    salary_min: Optional[str] = None
    salary_max: Optional[str] = None
    negotiable: Optional[bool] = None
    jd: Optional[str] = None
    skills: Optional[List[str]] = None
    experience: Optional[str] = None
    education: Optional[str] = None
    deadline: Optional[datetime] = None
    vacancies: Optional[int] = None
    documents: Optional[List[str]] = None
    status: Optional[str] = None


class JobOut(BaseModel):
    id: str
    company_id: str
    company_name: Optional[str] = None
    company_logo: Optional[str] = None
    title: str
    department: Optional[str] = ""
    type: str
    location: str
    salary_min: Optional[str] = None
    salary_max: Optional[str] = None
    negotiable: bool
    jd: str
    skills: List[str]
    experience: Optional[str] = ""
    education: Optional[str] = ""
    deadline: Optional[str] = None
    vacancies: int
    documents: List[str]
    status: str
    ai_generated: bool
    created_at: str
    applicant_count: Optional[int] = 0
