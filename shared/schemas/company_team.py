from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

class CompanyMemberResponse(BaseModel):
    id: int
    company_id: int
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    role: str = "recruiter"
    status: str = "Active"
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CompanyInviteCreateRequest(BaseModel):
    email: EmailStr
    role: str = Field(default="recruiter", description="Company role: company_admin, recruiter, hiring_manager, interviewer")
    message: Optional[str] = None


class CompanyInviteResponse(BaseModel):
    id: str
    email: EmailStr
    role: str
    message: Optional[str] = None
    status: str = "Pending"
    sent_date: Optional[str] = None
    expires_at: Optional[datetime] = None
    invite_token: str
    activation_url: str

    class Config:
        from_attributes = True


class MemberRoleUpdateRequest(BaseModel):
    role: str = Field(..., description="Target role: company_admin, recruiter, hiring_manager, interviewer")


class MemberStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Target status: Active, Inactive, Suspended")


class InvitationAcceptRequest(BaseModel):
    token: str = Field(..., description="Secret invite token received via email/link")
    password: str = Field(..., min_length=6, description="Account password")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
