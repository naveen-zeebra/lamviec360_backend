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


class OAuthLoginRequest(BaseModel):
    provider: str = Field(..., description="Provider: google, zalo, linkedin, facebook")
    token: Optional[str] = Field(None, description="Client token (access_token or id_token)")
    code: Optional[str] = Field(None, description="OAuth authorization code")
    redirect_uri: Optional[str] = Field(None, description="OAuth redirect URI used during code request")
    code_verifier: Optional[str] = Field(None, description="PKCE code verifier if applicable")
    email: Optional[EmailStr] = Field(None, description="User email (if provided directly or client-verified)")
    name: Optional[str] = Field(None, description="User full name")
    avatar_url: Optional[str] = Field(None, description="User avatar image URL")
    provider_user_id: Optional[str] = Field(None, description="Provider unique user identifier")

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        clean = (v or "").strip().lower()
        if clean not in ("google", "zalo", "linkedin", "facebook"):
            raise ValueError(f"Unsupported OAuth provider: {v}. Must be google, zalo, linkedin, or facebook.")
        return clean

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().lower() if v else None


class GoogleLoginRequest(BaseModel):
    token: Optional[str] = None
    code: Optional[str] = None
    redirect_uri: Optional[str] = None
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    google_id: Optional[str] = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().lower() if v else None


class ZaloLoginRequest(BaseModel):
    token: Optional[str] = None
    code: Optional[str] = None
    code_verifier: Optional[str] = None
    redirect_uri: Optional[str] = None
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    zalo_id: Optional[str] = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().lower() if v else None


class LinkedInLoginRequest(BaseModel):
    token: Optional[str] = None
    code: Optional[str] = None
    redirect_uri: Optional[str] = None
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    linkedin_id: Optional[str] = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().lower() if v else None


class FacebookLoginRequest(BaseModel):
    token: Optional[str] = None
    code: Optional[str] = None
    redirect_uri: Optional[str] = None
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    facebook_id: Optional[str] = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().lower() if v else None
