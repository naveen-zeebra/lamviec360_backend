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
