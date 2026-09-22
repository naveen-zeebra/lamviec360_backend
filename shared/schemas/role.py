from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class PermissionBase(BaseModel):
    module: str
    action: str
    description: Optional[str] = None

class PermissionCreate(PermissionBase):
    pass

class PermissionOut(PermissionBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class RoleBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    is_active: bool = True

class RoleCreate(RoleBase):
    permission_ids: Optional[List[int]] = []

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    permission_ids: Optional[List[int]] = None

class RoleOut(RoleBase):
    id: int
    is_system: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    permissions: List[PermissionOut] = []

    class Config:
        from_attributes = True
