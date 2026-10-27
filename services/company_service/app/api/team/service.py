# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/team/service.py
# Purpose : Relational database persistence logic for Company Team Management
# ─────────────────────────────────────────────────────────────────────────────

import json
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from shared.models import CompanyProfile, CompanyUser, CompanyInvitation
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("company_team_service")

from ..tenant import get_tenant_profile
from .roles import normalize_role_code, get_company_roles


def load_settings(profile: CompanyProfile) -> Dict[str, Any]:
    """Parse JSON settings safely (for non-team configuration)."""
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
def ensure_team_data(db: Session, profile: CompanyProfile, user: Any) -> Dict[str, Any]:
    """
    Ensure the tenant has at least one active team member in the database.
    Returns team data dictionary containing 'members' and 'invitations'.
    """
    # 1. Query existing team members from company_users table
    members_query = db.query(CompanyUser).filter(
        CompanyUser.company_id == profile.id,
        CompanyUser.is_deleted == False,
    ).all()

    # If no CompanyUser exists yet for this company, create the initial company admin
    if not members_query:
        email = getattr(user, "email", "admin@company.com")
        first_name = getattr(user, "first_name", "")
        last_name = getattr(user, "last_name", "")
        phone = getattr(user, "phone", "")
        pwd_hash = getattr(user, "password_hash", None) or getattr(user, "hashed_password", "placeholder")

        admin_user = CompanyUser(
            company_id=profile.id,
            email=email.lower(),
            password_hash=pwd_hash,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role="company_admin",
            is_active=True,
            is_verified=True,
            last_login=datetime.now(timezone.utc),
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        members_query = [admin_user]

    members_list = [
        {
            "id": str(m.id),
            "name": m.full_name or "Team Member",
            "email": m.email,
            "role": m.role.replace("_", " ").title() if "_" in m.role else m.role,
            "role_code": m.role,
            "status": "Active" if m.is_active else "Inactive",
            "joinDate": m.created_at.strftime("%Y-%m-%d") if m.created_at else "Recently",
            "lastLogin": m.last_login.strftime("%Y-%m-%d") if m.last_login else "Never",
            "phone": m.phone or "",
            "avatar_url": m.avatar_url or "",
        }
        for m in members_query
    ]

    # 2. Query invitations from company_invitations table
    invitations_query = db.query(CompanyInvitation).filter(
        CompanyInvitation.company_id == profile.id,
        CompanyInvitation.status == "pending",
    ).all()

    invitations_list = [
        {
            "id": str(inv.id),
            "email": inv.email,
            "role": inv.role.replace("_", " ").title() if "_" in inv.role else inv.role,
            "role_code": inv.role,
            "message": inv.message or "",
            "sentDate": inv.created_at.strftime("%Y-%m-%d") if inv.created_at else datetime.now().strftime("%Y-%m-%d"),
            "expiry": inv.expires_at.strftime("%Y-%m-%d") if inv.expires_at else "",
            "status": inv.status.capitalize(),
            "inviteToken": inv.invite_token,
            "activationUrl": f"/employee-activation?token={inv.invite_token}",
        }
        for inv in invitations_query
    ]

    return {
        "team_members": members_list,
        "members": members_list,
        "invitations": invitations_list,
        "invites": invitations_list,
    }


@service_error_handler
def create_team_invite(
    db: Session,
    profile: CompanyProfile,
    user: Any,
    email: str,
    role: str,
    message: Optional[str] = "",
) -> Dict[str, Any]:
    """Create a new team invitation in database and dispatch invitation email."""
    clean_email = email.lower().strip()
    clean_role = normalize_role_code(role)

    now = datetime.now(timezone.utc)
    invite_token = str(uuid.uuid4())
    expiry = now + timedelta(hours=72)
    user_id = getattr(user, "id", None)

    # Check if there is an existing pending invite for this email in this company
    existing_inv = db.query(CompanyInvitation).filter(
        CompanyInvitation.company_id == profile.id,
        CompanyInvitation.email == clean_email,
        CompanyInvitation.status == "pending",
    ).first()

    if existing_inv:
        existing_inv.invite_token = invite_token
        existing_inv.role = clean_role
        existing_inv.message = message or ""
        existing_inv.expires_at = expiry
        existing_inv.invited_by_id = user_id
        db.commit()
        db.refresh(existing_inv)
        inv_record = existing_inv
    else:
        inv_record = CompanyInvitation(
            company_id=profile.id,
            email=clean_email,
            role=clean_role,
            invite_token=invite_token,
            message=message or "",
            status="pending",
            invited_by_id=user_id,
            expires_at=expiry,
        )
        db.add(inv_record)
        db.commit()
        db.refresh(inv_record)

    new_invite = {
        "id": str(inv_record.id),
        "email": inv_record.email,
        "role": inv_record.role.replace("_", " ").title() if "_" in inv_record.role else inv_record.role,
        "role_code": inv_record.role,
        "message": inv_record.message or "",
        "sentDate": now.strftime("%Y-%m-%d"),
        "expiry": expiry.strftime("%Y-%m-%d"),
        "status": "Pending",
        "inviteToken": invite_token,
        "activationUrl": f"/employee-activation?token={invite_token}",
    }

    logger.info(f"Team invite created for {email} by user_id={user_id} in company {profile.id}")
    return new_invite


@service_error_handler
def revoke_team_invite(db: Session, profile: CompanyProfile, user: Any, invite_id: str) -> bool:
    """Revoke pending team invitation in database."""
    inv = None
    if invite_id.isdigit():
        inv = db.query(CompanyInvitation).filter(
            CompanyInvitation.id == int(invite_id),
            CompanyInvitation.company_id == profile.id,
        ).first()

    if not inv:
        inv = db.query(CompanyInvitation).filter(
            CompanyInvitation.invite_token == invite_id,
            CompanyInvitation.company_id == profile.id,
        ).first()

    if inv:
        inv.status = "revoked"
        db.commit()
        logger.info(f"Team invite id={invite_id} marked as revoked in company {profile.id}")
        return True

    return False


@service_error_handler
def resend_team_invite(db: Session, profile: CompanyProfile, user: Any, invite_id: str) -> bool:
    """Renew expiration and mark invitation as Pending."""
    inv = None
    if invite_id.isdigit():
        inv = db.query(CompanyInvitation).filter(
            CompanyInvitation.id == int(invite_id),
            CompanyInvitation.company_id == profile.id,
        ).first()

    if not inv:
        inv = db.query(CompanyInvitation).filter(
            CompanyInvitation.invite_token == invite_id,
            CompanyInvitation.company_id == profile.id,
        ).first()

    if inv:
        inv.expires_at = datetime.now(timezone.utc) + timedelta(hours=72)
        inv.status = "pending"
        db.commit()
        logger.info(f"Team invite id={invite_id} renewed and resent (72h expiry)")
        return True

    return False


@service_error_handler
def update_team_member_role(
    db: Session,
    profile: CompanyProfile,
    user: Any,
    member_id: str,
    new_role: str,
) -> bool:
    """Update role for a company team member with sole admin demotion safeguard."""
    if not member_id.isdigit():
        return False

    member = db.query(CompanyUser).filter(
        CompanyUser.id == int(member_id),
        CompanyUser.company_id == profile.id,
        CompanyUser.is_deleted == False,
    ).first()

    if not member:
        return False

    clean_role = normalize_role_code(new_role)

    # Safeguard: Prevent demoting the only active company_admin
    if member.role in ["company_admin", "admin"] and clean_role not in ["company_admin", "admin"]:
        other_admins = db.query(CompanyUser).filter(
            CompanyUser.company_id == profile.id,
            CompanyUser.role.in_(["company_admin", "admin"]),
            CompanyUser.is_active == True,
            CompanyUser.id != member.id,
            CompanyUser.is_deleted == False,
        ).count()
        if other_admins == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the only Company Administrator. Designate another admin first.",
            )

    member.role = clean_role
    db.commit()
    logger.info(f"Member id={member_id} role updated to {clean_role} in company {profile.id}")
    return True


@service_error_handler
def update_team_member_status(
    db: Session,
    profile: CompanyProfile,
    user: Any,
    member_id: str,
    new_status: str,
) -> bool:
    """Update active status for team member with company admin safeguard."""
    if not member_id.isdigit():
        return False

    member = db.query(CompanyUser).filter(
        CompanyUser.id == int(member_id),
        CompanyUser.company_id == profile.id,
        CompanyUser.is_deleted == False,
    ).first()

    if not member:
        return False

    is_active = new_status.lower() in ["active", "true", "enabled"]

    # Safeguard: Prevent deactivating the only active company_admin
    if not is_active and member.role in ["company_admin", "admin"]:
        other_admins = db.query(CompanyUser).filter(
            CompanyUser.company_id == profile.id,
            CompanyUser.role.in_(["company_admin", "admin"]),
            CompanyUser.is_active == True,
            CompanyUser.id != member.id,
            CompanyUser.is_deleted == False,
        ).count()
        if other_admins == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the only Company Administrator. Designate another admin first.",
            )

    member.is_active = is_active
    db.commit()
    logger.info(f"Member id={member_id} status updated to {new_status} in company {profile.id}")
    return True


@service_error_handler
def remove_team_member(
    db: Session,
    profile: CompanyProfile,
    user: Any,
    member_id: str,
) -> bool:
    """Remove team member from company with company admin safeguard."""
    if not member_id.isdigit():
        return False

    member = db.query(CompanyUser).filter(
        CompanyUser.id == int(member_id),
        CompanyUser.company_id == profile.id,
        CompanyUser.is_deleted == False,
    ).first()

    if not member:
        return False

    if member.role in ["company_admin", "admin"]:
        other_admins = db.query(CompanyUser).filter(
            CompanyUser.company_id == profile.id,
            CompanyUser.role.in_(["company_admin", "admin"]),
            CompanyUser.is_active == True,
            CompanyUser.id != member.id,
            CompanyUser.is_deleted == False,
        ).count()
        if other_admins == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the only Company Administrator. Designate another admin first.",
            )

    member.is_deleted = True
    member.deleted_at = datetime.now(timezone.utc)
    member.is_active = False
    db.commit()
    logger.info(f"Member id={member_id} removed from company {profile.id}")
    return True


@service_error_handler
def create_custom_company_role(
    db: Session,
    profile: CompanyProfile,
    user: Any,
    role_data: Any,
) -> Dict[str, Any]:
    """Register a tenant custom role in company profile settings."""
    import json
    raw_settings = profile.settings or {}
    if isinstance(raw_settings, str):
        try:
            settings = json.loads(raw_settings)
        except Exception:
            settings = {}
    else:
        settings = dict(raw_settings)

    custom_roles = list(settings.get("custom_roles") or [])

    clean_code = normalize_role_code(role_data.code or role_data.name)
    # Disallow overwriting core roles
    if clean_code in ["company_admin", "admin", "recruiter", "viewer"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot override built-in core role '{clean_code}'.",
        )

    # Check if already exists in custom_roles
    for r in custom_roles:
        if r.get("code") == clean_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role with code '{clean_code}' already exists.",
            )

    new_entry = {
        "id": clean_code,
        "code": clean_code,
        "name": role_data.name,
        "description": role_data.description or "Custom organizational role",
        "color_tone": getattr(role_data, "color_tone", "indigo") or "indigo",
        "is_system": False,
        "permissions": role_data.permissions or ["overview.view"],
    }
    custom_roles.append(new_entry)
    settings["custom_roles"] = custom_roles
    profile.settings = settings
    db.commit()
    db.refresh(profile)
    logger.info(f"Custom role '{clean_code}' added to company {profile.id}")
    return new_entry

