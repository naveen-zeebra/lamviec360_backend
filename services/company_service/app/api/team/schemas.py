from typing import Optional
from pydantic import BaseModel, EmailStr


class TeamInviteRequest(BaseModel):
    email: EmailStr
    role: str = "HR / Recruiter"
    message: Optional[str] = ""


class MemberRoleUpdateRequest(BaseModel):
    role: str


class MemberStatusUpdateRequest(BaseModel):
    status: str


class CustomRoleCreateRequest(BaseModel):
    code: str
    name: str
    description: Optional[str] = ""
    color_tone: Optional[str] = "indigo"
    permissions: list[str] = []
