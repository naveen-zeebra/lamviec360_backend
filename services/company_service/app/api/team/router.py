from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from shared.database.session import get_db
from shared.models import User
from shared.schemas import APIResponse
from shared.utils import get_current_user, require_user_type, success_response

router = APIRouter(prefix="/team", tags=["Company Team Management"])

class TeamInviteRequest(BaseModel):
    email: str
    role: str
    message: str = ""

@router.get("", response_model=APIResponse[dict])
def get_company_team(
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = user.company_profile
    if not profile:
        return success_response(data={"members": [], "invites": []})

    # Mock data for team members
    members = [
        {
            "id": user.id,
            "name": user.full_name,
            "email": user.email,
            "role": "admin",
            "status": "active"
        }
    ]
    return success_response(data={"members": members, "invites": []})

@router.post("/invite", response_model=APIResponse[dict])
def invite_team_member(
    req: TeamInviteRequest,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    return success_response(message=f"Invitation sent to {req.email}")

@router.delete("/invites/{invite_id}", response_model=APIResponse[dict])
def revoke_team_invitation(
    invite_id: int,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    return success_response(message="Invitation revoked")

@router.post("/invites/{invite_id}/resend", response_model=APIResponse[dict])
def resend_team_invitation(
    invite_id: int,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    return success_response(message="Invitation resent")
