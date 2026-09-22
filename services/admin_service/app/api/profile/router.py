from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from shared.database.session import get_db
from shared.models import User
from shared.schemas import APIResponse
from shared.utils import get_current_user, success_response

router = APIRouter(prefix="/profile", tags=["Admin Profile"])

class AdminProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None

class AvatarUpdate(BaseModel):
    avatar_url: str

@router.get("/me", response_model=APIResponse[dict])
def get_admin_me(user: User = Depends(get_current_user)):
    roles = [r.name for r in user.roles]
    role_codes = [r.code for r in user.roles]
    permissions = []
    for r in user.roles:
        for p in r.permissions:
            permissions.append(f"{p.module}:{p.action}")

    return success_response(
        data={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "name": user.full_name,
            "phone": user.phone,
            "avatar": user.avatar_url,
            "avatar_url": user.avatar_url,
            "role": roles[0] if roles else "Super Admin",
            "roles": role_codes,
            "permissions": list(set(permissions)),
            "user_type": user.user_type,
            "is_superuser": user.is_superuser,
            "created_at": user.created_at,
        }
    )

@router.put("/me", response_model=APIResponse[dict])
def update_admin_me(
    data: AdminProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.full_name:
        user.full_name = data.full_name
    if data.phone is not None:
        user.phone = data.phone
    if data.avatar_url is not None:
        user.avatar_url = data.avatar_url

    db.commit()
    db.refresh(user)

    return success_response(
        data={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "avatar": user.avatar_url,
        },
        message="Profile updated successfully",
    )

@router.post("/avatar", response_model=APIResponse[dict])
def update_avatar(
    data: AvatarUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.avatar_url = data.avatar_url
    db.commit()
    return success_response(data={"avatar_url": user.avatar_url}, message="Avatar updated successfully")
