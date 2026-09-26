import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from shared.database.session import get_db
from shared.models import User, CompanyProfile
from shared.schemas import APIResponse
from shared.utils import require_user_type, success_response

router = APIRouter(prefix="/team", tags=["Company Team Management"])


class TeamInviteRequest(BaseModel):
    email: EmailStr
    role: str = "HR / Recruiter"
    message: Optional[str] = ""


class MemberRoleUpdateRequest(BaseModel):
    role: str


class MemberStatusUpdateRequest(BaseModel):
    status: str


def _get_tenant_profile(user: User, db: Session) -> CompanyProfile:
    profile = user.company_profile
    if not profile:
        profile = CompanyProfile(
            user_id=user.id,
            company_name=user.full_name or "My Company",
            settings=json.dumps({}),
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def _load_settings(profile: CompanyProfile) -> dict:
    if not profile.settings:
        return {}
    if isinstance(profile.settings, dict):
        return profile.settings
    try:
        return json.loads(profile.settings)
    except Exception:
        return {}


def _save_settings(profile: CompanyProfile, settings_data: dict, db: Session):
    profile.settings = json.dumps(settings_data)
    db.commit()
    db.refresh(profile)


def _ensure_team_data(profile: CompanyProfile, user: User, db: Session) -> dict:
    settings = _load_settings(profile)
    updated = False

    if "team_members" not in settings or not isinstance(settings["team_members"], list):
        created_str = user.created_at.strftime("%Y-%m-%d") if user.created_at else datetime.now().strftime("%Y-%m-%d")
        settings["team_members"] = [
            {
                "id": str(user.id),
                "name": user.full_name or "Company Admin",
                "email": user.email,
                "role": "Company Admin",
                "status": "Active",
                "joinDate": created_str,
                "lastLogin": "Today",
            }
        ]
        updated = True

    if "invitations" not in settings or not isinstance(settings["invitations"], list):
        settings["invitations"] = []
        updated = True

    if updated:
        _save_settings(profile, settings, db)

    return settings


@router.get("", response_model=APIResponse[dict])
def get_company_team(
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = _get_tenant_profile(user, db)
    settings = _ensure_team_data(profile, user, db)

    return success_response(
        data={
            "members": settings.get("team_members", []),
            "invites": settings.get("invitations", []),
            "invitations": settings.get("invitations", []),
        },
        message="Team members and invitations retrieved",
    )


@router.post("/invite", response_model=APIResponse[dict])
def invite_team_member(
    req: TeamInviteRequest,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = _get_tenant_profile(user, db)
    settings = _ensure_team_data(profile, user, db)

    invitations = settings.get("invitations", [])
    now = datetime.now()
    invite_token = str(uuid.uuid4())

    new_invite = {
        "id": f"INV-{int(time.time() * 1000)}",
        "email": req.email.lower().strip(),
        "role": req.role,
        "message": req.message or "",
        "sentDate": now.strftime("%Y-%m-%d"),
        "expiry": (now + timedelta(days=7)).strftime("%Y-%m-%d"),
        "status": "Pending",
        "inviteToken": invite_token,
        "activationUrl": f"/employee-activation?token={invite_token}",
    }

    # Remove previous pending invite for same email if exists
    invitations = [i for i in invitations if i.get("email") != new_invite["email"]]
    invitations.insert(0, new_invite)
    settings["invitations"] = invitations

    _save_settings(profile, settings, db)

    return success_response(
        data=new_invite,
        message=f"Invitation sent to {req.email}",
    )


@router.delete("/invites/{invite_id}", response_model=APIResponse[dict])
def revoke_team_invitation(
    invite_id: str,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = _get_tenant_profile(user, db)
    settings = _ensure_team_data(profile, user, db)

    invitations = settings.get("invitations", [])
    found = False
    for inv in invitations:
        if str(inv.get("id")) == str(invite_id):
            inv["status"] = "Revoked"
            found = True
            break

    if not found:
        # Also remove if not matched
        invitations = [i for i in invitations if str(i.get("id")) != str(invite_id)]

    settings["invitations"] = invitations
    _save_settings(profile, settings, db)

    return success_response(message="Invitation revoked")


@router.post("/invites/{invite_id}/resend", response_model=APIResponse[dict])
def resend_team_invitation(
    invite_id: str,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = _get_tenant_profile(user, db)
    settings = _ensure_team_data(profile, user, db)

    invitations = settings.get("invitations", [])
    now = datetime.now()
    found = False

    for inv in invitations:
        if str(inv.get("id")) == str(invite_id):
            inv["sentDate"] = now.strftime("%Y-%m-%d")
            inv["expiry"] = (now + timedelta(days=7)).strftime("%Y-%m-%d")
            inv["status"] = "Pending"
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="Invitation not found")

    settings["invitations"] = invitations
    _save_settings(profile, settings, db)

    return success_response(message="Invitation resent successfully")


@router.patch("/members/{member_id}/role", response_model=APIResponse[dict])
def update_member_role(
    member_id: str,
    req: MemberRoleUpdateRequest,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = _get_tenant_profile(user, db)
    settings = _ensure_team_data(profile, user, db)

    members = settings.get("team_members", [])
    found = False
    for m in members:
        if str(m.get("id")) == str(member_id):
            m["role"] = req.role
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="Team member not found")

    settings["team_members"] = members
    _save_settings(profile, settings, db)

    return success_response(message=f"Role updated to {req.role}")


@router.patch("/members/{member_id}/status", response_model=APIResponse[dict])
def update_member_status(
    member_id: str,
    req: MemberStatusUpdateRequest,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = _get_tenant_profile(user, db)
    settings = _ensure_team_data(profile, user, db)

    members = settings.get("team_members", [])
    found = False
    for m in members:
        if str(m.get("id")) == str(member_id):
            m["status"] = req.status
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="Team member not found")

    settings["team_members"] = members
    _save_settings(profile, settings, db)

    return success_response(message=f"Member status updated to {req.status}")
