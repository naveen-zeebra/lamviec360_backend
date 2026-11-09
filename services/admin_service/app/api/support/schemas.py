# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/support/schemas.py
# Purpose : Pydantic schemas for Customer Support Console (sa12, SAP-FR-010)
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class SupportMessageResponse(BaseModel):
    id: int
    ticket_id: int
    sender_type: str  # USER, ADMIN, SYSTEM
    sender_name: str
    sender_email: Optional[str] = None
    message_body: str
    is_internal_note: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class SupportMessageCreate(BaseModel):
    message_body: str = Field(..., min_length=1, description="Message content")
    is_internal_note: bool = Field(default=False, description="True if only visible to admins")


class SupportStatusUpdate(BaseModel):
    status: str = Field(..., description="OPEN, IN_PROGRESS, RESOLVED, CLOSED")
    resolution_note: Optional[str] = None


class LinkedEntityInfo(BaseModel):
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    user_role: Optional[str] = None

    company_id: Optional[int] = None
    company_name: Optional[str] = None
    company_status: Optional[str] = None
    company_plan: Optional[str] = None

    job_id: Optional[int] = None
    job_title: Optional[str] = None
    job_status: Optional[str] = None


class SupportTicketListItem(BaseModel):
    id: int
    ticket_number: str
    subject: str
    category: str
    priority: str
    status: str
    submitter_name: str
    submitter_email: str
    submitter_role: str
    company_name: Optional[str] = None
    company_id: Optional[int] = None
    job_title: Optional[str] = None
    job_id: Optional[int] = None
    assigned_admin_name: Optional[str] = None
    message_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SupportTicketDetailResponse(BaseModel):
    id: int
    ticket_number: str
    subject: str
    category: str
    priority: str
    status: str
    submitter_name: str
    submitter_email: str
    submitter_role: str
    resolution_note: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    linked_record: LinkedEntityInfo
    messages: List[SupportMessageResponse] = []

    class Config:
        from_attributes = True


class SupportTicketCreateRequest(BaseModel):
    subject: str = Field(..., min_length=3, max_length=255)
    category: str = Field(default="ACCOUNT")  # ACCOUNT, BILLING, TECHNICAL, CONTENT, OTHER
    priority: str = Field(default="MEDIUM")  # LOW, MEDIUM, HIGH, URGENT
    message: str = Field(..., min_length=5)
    submitter_name: str
    submitter_email: str
    submitter_role: str = "JOBSEEKER"
    company_id: Optional[int] = None
    job_id: Optional[int] = None
    user_id: Optional[int] = None



class SupportCustomerReplyRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Customer reply content")
    submitter_name: Optional[str] = None


class SupportTicketTrackResponse(BaseModel):
    id: int
    ticket_number: str
    subject: str
    category: str
    priority: str
    status: str
    submitter_name: str
    submitter_email: str
    submitter_role: str
    resolution_note: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    messages: List[SupportMessageResponse] = []

    class Config:
        from_attributes = True
