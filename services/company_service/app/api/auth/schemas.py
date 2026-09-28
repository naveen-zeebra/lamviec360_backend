import re
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class CompanyRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    company_name: str = Field(..., min_length=1, max_length=255)
    contact_name: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    company_size: Optional[str] = None
    website: Optional[str] = None
    reg_number: Optional[str] = None
    tax_id: Optional[str] = None
    tax_code: Optional[str] = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class CompanyLoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class LoginInitiateRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class VerifyOtpRequest(BaseModel):
    session_token: str
    code: str


class SendVerificationEmailRequest(BaseModel):
    email: Optional[EmailStr] = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().lower() if v else None


class VerifyEmailRequest(BaseModel):
    email: Optional[EmailStr] = None
    code: str = Field(..., min_length=4, max_length=10)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().lower() if v else None


class ActivateInviteRequest(BaseModel):
    invite_token: str
    name: str
    password: str = Field(..., min_length=6)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    old_password: Optional[str] = None
    current_password: Optional[str] = None
    new_password: str = Field(..., min_length=6)

    @model_validator(mode="after")
    def resolve_current_password(self):
        if not self.old_password and self.current_password:
            self.old_password = self.current_password
        elif not self.old_password and not self.current_password:
            raise ValueError("Current password is required")
        return self
