from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from shared.schemas.jobseeker import JobSeekerProfileOut
from shared.schemas.job import JobPostingOut

class ApplicationCreate(BaseModel):
    job_id: int
    cover_letter: Optional[str] = None
    resume_url: Optional[str] = None

class ApplicationStatusUpdate(BaseModel):
    status: str = Field(..., description="applied, reviewing, shortlisted, interview, rejected, hired")
    recruiter_notes: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)

class ApplicationOut(BaseModel):
    id: int
    job_id: int
    jobseeker_id: int
    cover_letter: Optional[str] = None
    resume_url: Optional[str] = None
    status: str
    recruiter_notes: Optional[str] = None
    rating: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Nested relations when requested
    job: Optional[JobPostingOut] = None
    jobseeker: Optional[JobSeekerProfileOut] = None

    class Config:
        from_attributes = True
