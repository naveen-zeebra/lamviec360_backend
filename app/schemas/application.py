from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class ApplicationApplyRequest(BaseModel):
    job_id: str
    resume_file_name: Optional[str] = None
    cover_letter: Optional[str] = ""
    answers: Optional[Dict[str, Any]] = None


class ApplicationStageUpdate(BaseModel):
    stage: str
    rejection_template_id: Optional[str] = None
    rejection_note: Optional[str] = None


class BulkStageUpdateRequest(BaseModel):
    application_ids: List[str]
    stage: str
    rejection_template_id: Optional[str] = None
    rejection_note: Optional[str] = None


class AddNoteRequest(BaseModel):
    text: str


class NoteOut(BaseModel):
    id: str
    text: str
    author: str
    at: str


class TimelineEventOut(BaseModel):
    stage: str
    date: str


class CandidateOut(BaseModel):
    id: str
    job_id: str
    job_title: Optional[str] = ""
    name: str
    email: str
    phone: Optional[str] = ""
    experience_years: Optional[int] = 0
    education_level: Optional[str] = ""
    applied_date: str
    stage: str
    match_score: int
    resume_file_name: Optional[str] = ""
    notes: List[NoteOut] = []
    interview: Optional[Dict[str, Any]] = None
    rejection_template_id: Optional[str] = None
    rejection_note: Optional[str] = None
    rejected_at: Optional[str] = None
