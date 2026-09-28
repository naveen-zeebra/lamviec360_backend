# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/profile/router.py
# Purpose : Presentation layer (FastAPI endpoints) for Platform Administrator Profile
# ─────────────────────────────────────────────────────────────────────────────

from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.schemas import APIResponse
from shared.utils import get_current_user, success_response

from .schemas import AdminProfileUpdate, AvatarUpdate
from .controller import (
    get_admin_me_controller,
    update_admin_me_controller,
    update_avatar_controller,
)

router = APIRouter(prefix="/profile", tags=["Admin Profile"])


@router.get("/me", response_model=APIResponse[dict], summary="Get Current Admin Profile")
def get_admin_me(user: Any = Depends(get_current_user)):
    return success_response(data=get_admin_me_controller(user))


@router.put("/me", response_model=APIResponse[dict], summary="Update Current Admin Profile")
def update_admin_me(
    data: AdminProfileUpdate,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return success_response(
        data=update_admin_me_controller(data, user, db),
        message="Profile updated successfully",
    )


@router.post("/avatar", response_model=APIResponse[dict], summary="Update Admin Avatar")
def update_avatar(
    data: AvatarUpdate,
    user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return success_response(
        data=update_avatar_controller(data, user, db),
        message="Avatar updated successfully",
    )
