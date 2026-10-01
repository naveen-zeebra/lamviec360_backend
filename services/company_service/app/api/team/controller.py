# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/team/controller.py
# Purpose : Orchestration layer for Company Team Management
# ─────────────────────────────────────────────────────────────────────────────

from typing import Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from shared.utils.logger import get_logger

from . import service
from .schemas import TeamInviteRequest, MemberRoleUpdateRequest, MemberStatusUpdateRequest

logger = get_logger("company_team_controller")


def get_company_team_controller(user: Any, db: Session) -> Dict[str, Any]:
    """Retrieve list of team members and active/pending invitations."""
    profile = service.get_tenant_profile(db, user)
    settings = service.ensure_team_data(db, profile, user)
    return {
        "members": settings.get("team_members", []),
        "invites": settings.get("invitations", []),
        "invitations": settings.get("invitations", []),
    }


def invite_team_member_controller(req: TeamInviteRequest, user: Any, db: Session) -> Dict[str, Any]:
    """Invite a new team member and dispatch invitation."""
    profile = service.get_tenant_profile(db, user)
    return service.create_team_invite(
        db=db,
        profile=profile,
        user=user,
        email=req.email,
        role=req.role,
        message=req.message,
    )


def revoke_team_invitation_controller(invite_id: str, user: Any, db: Session) -> None:
    """Revoke pending team invitation."""
    profile = service.get_tenant_profile(db, user)
    revoked = service.revoke_team_invite(db, profile, user, invite_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="Invitation not found")


def resend_team_invitation_controller(invite_id: str, user: Any, db: Session) -> None:
    """Resend and refresh invitation expiration."""
    profile = service.get_tenant_profile(db, user)
    found = service.resend_team_invite(db, profile, user, invite_id)
    if not found:
        raise HTTPException(status_code=404, detail="Invitation not found")


def update_member_role_controller(member_id: str, req: MemberRoleUpdateRequest, user: Any, db: Session) -> None:
    """Update team member role."""
    profile = service.get_tenant_profile(db, user)
    found = service.update_team_member_role(db, profile, user, member_id, req.role)
    if not found:
        raise HTTPException(status_code=404, detail="Team member not found")


def update_member_status_controller(member_id: str, req: MemberStatusUpdateRequest, user: Any, db: Session) -> None:
    """Update team member status."""
    profile = service.get_tenant_profile(db, user)
    found = service.update_team_member_status(db, profile, user, member_id, req.status)
    if not found:
        raise HTTPException(status_code=404, detail="Team member not found")


def remove_team_member_controller(member_id: str, user: Any, db: Session) -> None:
    """Remove team member from company."""
    profile = service.get_tenant_profile(db, user)
    found = service.remove_team_member(db, profile, user, member_id)
    if not found:
        raise HTTPException(status_code=404, detail="Team member not found")
