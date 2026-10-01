# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/team/router.py
# Purpose : Presentation layer (FastAPI endpoints) for Company Team Management
# ─────────────────────────────────────────────────────────────────────────────

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.schemas import APIResponse
from shared.utils import get_current_company_user, success_response

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
    remove_team_member_controller,
)

router = APIRouter(prefix="/team", tags=["Company Team Management"])


def require_company_admin_role(user: Any = Depends(get_current_company_user)) -> Any:
    """Ensure the authenticated company user holds administrator privileges."""
    if getattr(user, "is_superuser", False):
        return user
    user_role = getattr(user, "role", None) or getattr(user, "user_type", None)
    if user_role not in ["company_admin", "admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Company Administrators can perform team modifications",
        )
    return user


@router.get("", response_model=APIResponse[dict], summary="Get Team Members & Invitations")
def get_company_team(
    user: Any = Depends(get_current_company_user),
    db: Session = Depends(get_db),
):
    """Retrieve list of team members and active/pending invitations for caller's company."""
    data = get_company_team_controller(user, db)
    return success_response(
        data=data,
        message="Team members and invitations retrieved",
    )


@router.post("/invite", response_model=APIResponse[dict], summary="Invite Team Member")
def invite_team_member(
    req: TeamInviteRequest,
    user: Any = Depends(require_company_admin_role),
    db: Session = Depends(get_db),
):
    """Dispatch invitation to a new employee. Restricted to Company Admins."""
    invite = invite_team_member_controller(req, user, db)
    return success_response(
        data=invite,
        message=f"Invitation sent to {req.email}",
    )


@router.delete("/invites/{invite_id}", response_model=APIResponse[dict], summary="Revoke Team Invitation")
def revoke_team_invitation(
    invite_id: str,
    user: Any = Depends(require_company_admin_role),
    db: Session = Depends(get_db),
):
    """Revoke a pending team invitation. Restricted to Company Admins."""
    revoke_team_invitation_controller(invite_id, user, db)
    return success_response(message="Invitation revoked")


@router.post("/invites/{invite_id}/resend", response_model=APIResponse[dict], summary="Resend Team Invitation")
def resend_team_invitation(
    invite_id: str,
    user: Any = Depends(require_company_admin_role),
    db: Session = Depends(get_db),
):
    """Resend and refresh an existing invitation. Restricted to Company Admins."""
    resend_team_invitation_controller(invite_id, user, db)
    return success_response(message="Invitation resent successfully")


@router.patch("/members/{member_id}/role", response_model=APIResponse[dict], summary="Update Member Role")
def update_member_role(
    member_id: str,
    req: MemberRoleUpdateRequest,
    user: Any = Depends(require_company_admin_role),
    db: Session = Depends(get_db),
):
    """Update role for a team member. Restricted to Company Admins."""
    update_member_role_controller(member_id, req, user, db)
    return success_response(message=f"Role updated to {req.role}")


@router.patch("/members/{member_id}/status", response_model=APIResponse[dict], summary="Update Member Status")
def update_member_status(
    member_id: str,
    req: MemberStatusUpdateRequest,
    user: Any = Depends(require_company_admin_role),
    db: Session = Depends(get_db),
):
    """Activate or deactivate team member. Restricted to Company Admins."""
    update_member_status_controller(member_id, req, user, db)
    return success_response(message=f"Member status updated to {req.status}")


@router.delete("/members/{member_id}", response_model=APIResponse[dict], summary="Remove Member from Company")
def remove_team_member(
    member_id: str,
    user: Any = Depends(require_company_admin_role),
    db: Session = Depends(get_db),
):
    """Remove team member from company tenant. Restricted to Company Admins."""
    remove_team_member_controller(member_id, user, db)
    return success_response(message="Member removed successfully")
