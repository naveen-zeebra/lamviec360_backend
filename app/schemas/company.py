from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    reg_number: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    logo: Optional[str] = None


class QuotaOut(BaseModel):
    plan: str
    limit: Optional[int]
    used: int
    remaining: Optional[int]


class CompanyOut(BaseModel):
    id: str
    name: str
    reg_number: Optional[str]
    industry: str
    size: str
    website: Optional[str]
    description: Optional[str]
    logo: Optional[str]
    verified: bool
    email_verified: bool
    approval_status: str
    plan: str
    quota: QuotaOut
    settings: Optional[Dict[str, Any]] = None


class TeamMemberOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    status: str
    created_at: datetime
    last_login: Optional[str] = None


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: str = "HR / Recruiter"
    message: Optional[str] = ""


class InvitationOut(BaseModel):
    id: str
    email: str
    role: str
    message: str
    status: str
    sent_date: datetime
    expiry: datetime


class RejectionTemplateRequest(BaseModel):
    title: str
    body: str


class RejectionTemplateOut(BaseModel):
    id: str
    title: str
    body: str
