# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/team/router.py
# Purpose : Presentation layer (FastAPI endpoints) for Company Team Management
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import User
from shared.schemas import APIResponse
from shared.utils import require_user_type, success_response

from .schemas import (
    TeamInviteRequest,
    MemberRoleUpdateRequest,
    MemberStatusUpdateRequest,
)
from .controller import (
    get_company_team_controller,
    invite_team_member_controller,
    revoke_team_invitation_controller,
    resend_team_invitation_controller,
    update_member_role_controller,
    update_member_status_controller,
)

router = APIRouter(prefix="/team", tags=["Company Team Management"])


@router.get("", response_model=APIResponse[dict], summary="Get Team Members & Invitations")
def get_company_team(
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    data = get_company_team_controller(user, db)
    return success_response(
        data=data,
        message="Team members and invitations retrieved",
    )


@router.post("/invite", response_model=APIResponse[dict], summary="Invite Team Member")
def invite_team_member(
    req: TeamInviteRequest,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    invite = invite_team_member_controller(req, user, db)
    return success_response(
        data=invite,
        message=f"Invitation sent to {req.email}",
    )


@router.delete("/invites/{invite_id}", response_model=APIResponse[dict], summary="Revoke Team Invitation")
def revoke_team_invitation(
    invite_id: str,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    revoke_team_invitation_controller(invite_id, user, db)
    return success_response(message="Invitation revoked")


@router.post("/invites/{invite_id}/resend", response_model=APIResponse[dict], summary="Resend Team Invitation")
def resend_team_invitation(
    invite_id: str,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    resend_team_invitation_controller(invite_id, user, db)
    return success_response(message="Invitation resent successfully")


@router.patch("/members/{member_id}/role", response_model=APIResponse[dict], summary="Update Member Role")
def update_member_role(
    member_id: str,
    req: MemberRoleUpdateRequest,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    update_member_role_controller(member_id, req, user, db)
    return success_response(message=f"Role updated to {req.role}")


@router.patch("/members/{member_id}/status", response_model=APIResponse[dict], summary="Update Member Status")
def update_member_status(
    member_id: str,
    req: MemberStatusUpdateRequest,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    update_member_status_controller(member_id, req, user, db)
    return success_response(message=f"Member status updated to {req.status}")
