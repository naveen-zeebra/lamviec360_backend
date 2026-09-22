from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from shared.schemas.role import RoleOut

class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = None
    user_type: str = "jobseeker"  # super_admin, admin, company, jobseeker
    is_active: bool = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    role_ids: Optional[List[int]] = []

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None
    role_ids: Optional[List[int]] = None

class UserOut(UserBase):
    id: int
    avatar_url: Optional[str] = None
    is_verified: bool = False
    is_superuser: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    roles: List[RoleOut] = []

    class Config:
        from_attributes = True
