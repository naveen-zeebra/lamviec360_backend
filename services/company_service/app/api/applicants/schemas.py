from typing import Optional, List, Union
from pydantic import BaseModel, Field


class ApplicantStatusUpdateSchema(BaseModel):
    status: str
    recruiter_notes: Optional[str] = None
    rating: Optional[int] = None


class BulkStageRequest(BaseModel):
    application_ids: List[Union[int, str]]
    status: str
    rejection_template_id: Optional[Union[int, str]] = None
    rejection_note: Optional[str] = None


class CandidateNoteRequest(BaseModel):
    text: str


class ScheduleInterviewRequest(BaseModel):
    round_name: str
    scheduled_at: str
    duration_min: int = 45
    mode: str = "video"
    location_or_link: str
    instructions: Optional[str] = ""
    interviewers: Optional[List[str]] = []
    documents: Optional[List[str]] = []
