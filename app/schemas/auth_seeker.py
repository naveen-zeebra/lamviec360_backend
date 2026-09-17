from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class SeekerRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    confirm_password: Optional[str] = None


class SeekerVerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=4, max_length=10)


class SeekerLoginRequest(BaseModel):
    email: EmailStr
    password: str


class SeekerGoogleLoginRequest(BaseModel):
    id_token: Optional[str] = None
    email: EmailStr
    name: str


class SeekerTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str = "Job Seeker"
    user_id: str
    name: str
    email: str
    email_verified: bool
