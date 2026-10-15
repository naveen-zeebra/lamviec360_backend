# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/resumes/schemas.py
# Purpose : Pydantic schemas for JobSeekerResume endpoints
# ─────────────────────────────────────────────────────────────────────────────
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ResumeItem(BaseModel):
    id: int
    file_name: str
    file_url: str
    mime_type: Optional[str] = None
    size_bytes: int = 0
    is_default: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class ResumeListResponse(BaseModel):
    items: List[Dict[str, Any]]
    count: int
    max: int = 5
