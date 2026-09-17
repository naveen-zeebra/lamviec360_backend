from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class InterviewerInfo(BaseModel):
    name: str
    role: str


class InterviewCreateRequest(BaseModel):
    round_name: str = "First round – Technical"
    scheduled_at: datetime
    duration_min: int = 45
    mode: str = "video"
    location_or_link: str = ""
    instructions: Optional[str] = ""
    interviewers: List[Dict[str, str]] = []
    documents: List[str] = ["CV / Resume"]


class InterviewRespondRequest(BaseModel):
    status: str  # "confirmed" or "declined"
    note: Optional[str] = ""


class InterviewOut(BaseModel):
    id: str
    application_id: str
    job_id: str
    job_title: Optional[str] = ""
    company_name: Optional[str] = ""
    round_name: str
    scheduled_at: str
    duration_min: int
    mode: str
    location_or_link: str
    instructions: str
    interviewers: List[Dict[str, str]]
    documents: List[str]
    status: str
    response_note: Optional[str] = None
    response_at: Optional[str] = None
