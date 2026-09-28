from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


class UserCreateSchema(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None
    phone: Optional[str] = None
    user_type: str = "jobseeker"
    is_active: bool = True
    role_ids: Optional[List[int]] = []


class UserUpdateSchema(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None
    role_ids: Optional[List[int]] = None


class AssignRolesRequest(BaseModel):
    role_ids: List[int]
