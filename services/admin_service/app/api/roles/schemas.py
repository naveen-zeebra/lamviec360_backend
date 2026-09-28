# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/roles/schemas.py
# Purpose : Pydantic schemas for Role & Permission Management
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List
from pydantic import BaseModel, Field


class RolePermissionSchema(BaseModel):
    id: int
    module_key: Optional[str] = None
    module: Optional[str] = None
    can_view: bool = False
    can_create: bool = False
    can_edit: bool = False
    can_delete: bool = False
    action: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class RoleCreateSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    is_active: bool = True
    permission_ids: Optional[List[int]] = []


class RoleUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    permission_ids: Optional[List[int]] = None
