# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/admin_users/schemas.py
# Purpose : Schemas for Dedicated Platform Administrator Management
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


class AdminUserCreateSchema(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    phone: Optional[str] = None
    role: str = "Operations Admin"
    is_active: bool = True


class AdminUserUpdateSchema(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class PermissionUpdateItem(BaseModel):
    module_key: str
    can_view: bool
    can_create: bool
    can_edit: bool
    can_delete: bool


class RoleUpdateRequest(BaseModel):
    permissions: List[PermissionUpdateItem]
