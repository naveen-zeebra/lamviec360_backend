from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = None
    user_type: str = Field(default="jobseeker")  # "jobseeker" or "company"
    company_name: Optional[str] = None  # if company registration

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None
    expires_in: int = 3600
    user: Optional[Dict[str, Any]] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: Optional[str] = None
    email: Optional[EmailStr] = None
    code: Optional[str] = None
    new_password: str = Field(..., min_length=6)

class SendVerificationEmailRequest(BaseModel):
    email: Optional[EmailStr] = None

class VerifyEmailRequest(BaseModel):
    email: Optional[EmailStr] = None
    code: str = Field(..., min_length=4, max_length=10)

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)

