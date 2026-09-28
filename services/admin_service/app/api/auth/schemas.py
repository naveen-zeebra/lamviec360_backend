import re
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator, model_validator


class AdminLoginRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "admin@example.com",
                "password": "Password123!",
            }
        }
    }

    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        errors = []
        if len(v) < 8:
            errors.append("at least 8 characters")
        if not re.search(r"[A-Z]", v):
            errors.append("an uppercase letter")
        if not re.search(r"[a-z]", v):
            errors.append("a lowercase letter")
        if not re.search(r"\d", v):
            errors.append("a number")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            errors.append("a special character (!@#$%^&* etc.)")
        if errors:
            raise ValueError("Password must contain " + ", ".join(errors))
        return v


class ChangePasswordRequest(BaseModel):
    old_password: Optional[str] = None
    current_password: Optional[str] = None
    new_password: str

    @model_validator(mode="after")
    def resolve_current_password(self):
        # Allow either current_password or old_password for frontend flexibility
        if not self.old_password and self.current_password:
            self.old_password = self.current_password
        elif not self.old_password and not self.current_password:
            raise ValueError("Current password is required")
        return self

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        errors = []
        if len(v) < 8:
            errors.append("at least 8 characters")
        if not re.search(r"[A-Z]", v):
            errors.append("an uppercase letter")
        if not re.search(r"[a-z]", v):
            errors.append("a lowercase letter")
        if not re.search(r"\d", v):
            errors.append("a number")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            errors.append("a special character (!@#$%^&* etc.)")
        if errors:
            raise ValueError("Password must contain " + ", ".join(errors))
        return v
