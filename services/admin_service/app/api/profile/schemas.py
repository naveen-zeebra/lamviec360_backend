from typing import Optional
from pydantic import BaseModel


class AdminProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None


class AvatarUpdate(BaseModel):
    avatar_url: str
