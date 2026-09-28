import re
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class JobSeekerRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None
    phone: Optional[str] = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class JobSeekerLoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class RefreshTokenRequest(BaseModel):
    refresh_token: str


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


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class ResetPasswordRequest(BaseModel):
    token: Optional[str] = None
    email: Optional[EmailStr] = None
    code: Optional[str] = None
    new_password: str = Field(..., min_length=6)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().lower() if v else None
