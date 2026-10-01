# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/team/service.py
# Purpose : Domain & settings persistence logic for Company Team Management
# ─────────────────────────────────────────────────────────────────────────────

import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from shared.models import User, CompanyProfile
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("company_team_service")


from ..tenant import get_tenant_profile


def load_settings(profile: CompanyProfile) -> Dict[str, Any]:
    """Parse JSON settings safely."""
    if not profile.settings:
        return {}
    if isinstance(profile.settings, dict):
        return profile.settings
    try:
        return json.loads(profile.settings)
    except Exception:
        return {}


@service_error_handler
def save_settings(db: Session, profile: CompanyProfile, settings_data: dict) -> None:
    """Save updated settings dict to database."""
    profile.settings = json.dumps(settings_data)
    db.commit()
    db.refresh(profile)


@service_error_handler
def ensure_team_data(db: Session, profile: CompanyProfile, user: User) -> Dict[str, Any]:
    """Initialize team members and invitations list if not present in settings."""
    settings = load_settings(profile)
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
        save_settings(db, profile, settings)

    return settings


@service_error_handler
def create_team_invite(
    db: Session,
    profile: CompanyProfile,
    user: User,
    email: str,
    role: str,
    message: Optional[str] = "",
) -> Dict[str, Any]:
    """Create a new team invitation and update company settings."""
    settings = ensure_team_data(db, profile, user)
    invitations = settings.get("invitations", [])
    now = datetime.now()
    invite_token = str(uuid.uuid4())

    new_invite = {
        "id": f"INV-{int(time.time() * 1000)}",
        "email": email.lower().strip(),
        "role": role,
        "message": message or "",
        "sentDate": now.strftime("%Y-%m-%d"),
        "expiry": (now + timedelta(days=7)).strftime("%Y-%m-%d"),
        "status": "Pending",
        "inviteToken": invite_token,
        "activationUrl": f"/employee-activation?token={invite_token}",
    }

    invitations = [i for i in invitations if i.get("email") != new_invite["email"]]
    invitations.insert(0, new_invite)
    settings["invitations"] = invitations

    save_settings(db, profile, settings)
    logger.info(f"Team invite created for {email} by user_id={user.id}")
    return new_invite


@service_error_handler
def revoke_team_invite(db: Session, profile: CompanyProfile, user: User, invite_id: str) -> None:
    """Revoke or remove invitation."""
    settings = ensure_team_data(db, profile, user)
    invitations = settings.get("invitations", [])
    found = False
    for inv in invitations:
        if str(inv.get("id")) == str(invite_id):
            inv["status"] = "Revoked"
            found = True
            break

    if not found:
        invitations = [i for i in invitations if str(i.get("id")) != str(invite_id)]

    settings["invitations"] = invitations
    save_settings(db, profile, settings)
    logger.info(f"Team invite id={invite_id} revoked")


@service_error_handler
def resend_team_invite(db: Session, profile: CompanyProfile, user: User, invite_id: str) -> bool:
    """Renew expiration and mark invitation as Pending."""
    settings = ensure_team_data(db, profile, user)
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

    if found:
        settings["invitations"] = invitations
        save_settings(db, profile, settings)
        logger.info(f"Team invite id={invite_id} resent")
        return True
    return False


@service_error_handler
def update_team_member_role(
    db: Session,
    profile: CompanyProfile,
    user: User,
    member_id: str,
    new_role: str,
) -> bool:
    """Update role string for team member."""
    settings = ensure_team_data(db, profile, user)
    members = settings.get("team_members", [])
    found = False

    for m in members:
        if str(m.get("id")) == str(member_id):
            m["role"] = new_role
            found = True
            break

    if found:
        settings["team_members"] = members
        save_settings(db, profile, settings)
        logger.info(f"Member id={member_id} role updated to {new_role}")
        return True
    return False


@service_error_handler
def update_team_member_status(
    db: Session,
    profile: CompanyProfile,
    user: User,
    member_id: str,
    new_status: str,
) -> bool:
    """Update status string for team member."""
    settings = ensure_team_data(db, profile, user)
    members = settings.get("team_members", [])
    found = False

    for m in members:
        if str(m.get("id")) == str(member_id):
            m["status"] = new_status
            found = True
            break

    if found:
        settings["team_members"] = members
        save_settings(db, profile, settings)
        logger.info(f"Member id={member_id} status updated to {new_status}")
        return True
    return False
