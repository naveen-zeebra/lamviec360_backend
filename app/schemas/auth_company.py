from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class CompanyRegisterRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=200)
    contact_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    industry: str = Field(..., min_length=2, max_length=100)
    size: str = Field(..., min_length=1, max_length=50)
    reg_number: Optional[str] = None
    website: Optional[str] = None


class CompanyVerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=4, max_length=10)


class CompanyLoginInitiateRequest(BaseModel):
    email: EmailStr
    password: str


class CompanyLoginInitiateResponse(BaseModel):
    status: str  # "2FA_REQUIRED", "PENDING_APPROVAL", "REJECTED", "SUSPENDED"
    session_token: Optional[str] = None
    masked_email: Optional[str] = None
    message: str


class CompanyLoginVerifyOtpRequest(BaseModel):
    session_token: str
    code: str = Field(..., min_length=4, max_length=10)


class CompanyTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    company_id: str
    company_name: str
    user_id: str
    user_name: str
    user_email: str
    approval_status: str
    plan_id: str


class AcceptInviteRequest(BaseModel):
    invite_token: str
    name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=8)
