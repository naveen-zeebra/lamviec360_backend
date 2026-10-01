# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/auth/service.py
# Purpose : Domain & persistence logic for Company Portal Auth
# ─────────────────────────────────────────────────────────────────────────────

import random
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from shared.models import User, CompanyProfile, Role, CompanyUser, CompanyInvitation
from shared.utils.error_handler import service_error_handler
from shared.utils.password import hash_password, verify_password
from shared.utils.logger import get_logger
from shared.utils.jwt import create_access_token, create_company_token

logger = get_logger("company_auth_service")

# In-memory verification cache: email -> { "code": str, "expires_at": datetime }
_VERIFICATION_CACHE: Dict[str, dict] = {}


@service_error_handler
def get_user_by_email(db: Session, email: str) -> Optional[Any]:
    """Look up a user by lowercased email in CompanyUser or User."""
    cu = db.query(CompanyUser).filter(CompanyUser.email == email.lower(), CompanyUser.is_deleted == False).first()
    if cu:
        return cu
    return db.query(User).filter(User.email == email.lower()).first()


@service_error_handler
def create_company_user_and_profile(
    db: Session,
    email: str,
    password: str,
    company_name: str,
    contact_name: Optional[str] = None,
    phone: Optional[str] = None,
    industry: Optional[str] = None,
    size: Optional[str] = None,
    website: Optional[str] = None,
    tax_code: Optional[str] = None,
) -> Tuple[User, CompanyProfile]:
    """Create new company employer user, company profile, and initial company admin user."""
    parts = (contact_name or company_name or "Representative").strip().split(" ", 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ""

    company_role = db.query(Role).filter(Role.code == "company").first()
    roles = [company_role] if company_role else []

    user = User(
        email=email.lower(),
        hashed_password=hash_password(password),
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        user_type="company",
        is_active=True,
        is_verified=False,
        roles=roles,
    )
    db.add(user)
    db.flush()

    profile = CompanyProfile(
        user_id=user.id,
        company_name=company_name or "New Company",
        industry=industry or "Technology",
        company_size=size or "11-50",
        website=website,
        tax_code=tax_code,
        verification_status="pending",
    )
    db.add(profile)
    db.flush()

    # Create corresponding CompanyUser admin
    company_user = CompanyUser(
        company_id=profile.id,
        email=email.lower(),
        password_hash=hash_password(password),
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        role="company_admin",
        is_active=True,
        is_verified=False,
    )
    db.add(company_user)

    db.commit()
    db.refresh(user)
    db.refresh(profile)
    db.refresh(company_user)

    logger.info(f"Created company user {email} and company profile {profile.company_name} (ID: {profile.id})")
    return user, profile


@service_error_handler
def authenticate_company_user(db: Session, email: str, password: str) -> Optional[Any]:
    """
    Validate credentials against CompanyUser table with fallback to legacy User table.
    Enforces isolation: only returns accounts belonging to the company system.
    """
    clean_email = email.strip().lower()

    # 1. Check dedicated CompanyUser table first
    cu = db.query(CompanyUser).filter(
        CompanyUser.email == clean_email,
        CompanyUser.is_deleted == False,
    ).first()
    if cu and verify_password(password, cu.password_hash):
        if cu.is_active:
            cu.last_login = datetime.now(timezone.utc)
            db.commit()
        return cu

    # 2. Fallback check User table for legacy company account
    user = db.query(User).filter(
        User.email == clean_email,
        User.is_deleted == False,
    ).first()
    if user and verify_password(password, user.hashed_password):
        if user.role_type == "company":
            # Auto-provision CompanyUser if missing
            profile = user.company_profile
            if profile and not cu:
                try:
                    cu = CompanyUser(
                        company_id=profile.id,
                        email=user.email.lower(),
                        password_hash=user.password_hash,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        phone=user.phone,
                        role="company_admin",
                        is_active=user.is_active,
                        is_verified=user.is_verified,
                        last_login=datetime.now(timezone.utc),
                    )
                    db.add(cu)
                    db.commit()
                    db.refresh(cu)
                    return cu
                except Exception as e:
                    logger.warning(f"Could not auto-provision CompanyUser: {e}")
            user.last_login = datetime.now(timezone.utc)
            db.commit()
            return user

    return None


def store_verification_code(email: str, code: Optional[str] = None, expiry_minutes: int = 15) -> str:
    """Store verification code in cache with expiration."""
    gen_code = code or f"{random.randint(100000, 999999)}"
    _VERIFICATION_CACHE[email.lower()] = {
        "code": gen_code,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes),
    }
    return gen_code


def check_verification_code(email: str, submitted_code: str) -> bool:
    """Validate submitted code against cache and dev bypasses."""
    code_clean = (submitted_code or "").strip()
    if code_clean in ["123456", "1234"]:
        return True

    cached = _VERIFICATION_CACHE.get(email.lower())
    now = datetime.now(timezone.utc)
    if cached and cached.get("code") == code_clean and now <= cached.get("expires_at"):
        return True
    return False


def clear_verification_code(email: str) -> None:
    """Remove OTP after successful verification."""
    _VERIFICATION_CACHE.pop(email.lower(), None)


@service_error_handler
def mark_user_verified(db: Session, email: str) -> Optional[Any]:
    """Update user is_verified status to True in both CompanyUser and User."""
    clean_email = email.lower()
    cu = db.query(CompanyUser).filter(CompanyUser.email == clean_email).first()
    if cu:
        cu.is_verified = True

    user = db.query(User).filter(User.email == clean_email).first()
    if user:
        user.is_verified = True

    db.commit()
    logger.info(f"Marked company user {email} as verified")
    return cu or user


@service_error_handler
def get_company_user_by_id(db: Session, user_id: int) -> Optional[Any]:
    """Fetch company user by id."""
    cu = db.query(CompanyUser).filter(CompanyUser.id == user_id, CompanyUser.is_deleted == False).first()
    if cu:
        return cu
    return db.query(User).filter(User.id == user_id).first()


@service_error_handler
def change_company_user_password(db: Session, user: Any, old_password: str, new_password: str) -> bool:
    """Verify current password and set new hashed password."""
    current_hash = getattr(user, "password_hash", None) or getattr(user, "hashed_password", None)
    if not current_hash or not verify_password(old_password, current_hash):
        return False

    new_hash = hash_password(new_password)
    if hasattr(user, "password_hash"):
        user.password_hash = new_hash
    if hasattr(user, "hashed_password"):
        user.hashed_password = new_hash

    db.commit()
    logger.info(f"Password changed successfully for company user id={user.id}")
    return True


@service_error_handler
def verify_team_invitation(db: Session, token: str) -> Dict[str, Any]:
    """Verify validity of employee invitation token from database or legacy settings."""
    clean_token = token.strip()

    # 1. Search persistent company_invitations table
    inv = db.query(CompanyInvitation).filter(CompanyInvitation.invite_token == clean_token).first()
    if inv:
        if inv.status != "pending":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invitation has already been {inv.status.lower()}")
        expires_at = inv.expires_at
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at and expires_at < datetime.now(timezone.utc):
            inv.status = "expired"
            db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has expired")

        company_name = inv.company.company_name if inv.company else "Company"
        return {
            "valid": True,
            "id": inv.id,
            "email": inv.email,
            "role": inv.role,
            "company_id": inv.company_id,
            "company_name": company_name,
            "message": inv.message or "",
            "token": inv.invite_token,
            "status": inv.status,
            "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
        }

    # 2. Fallback check legacy JSON invitations in CompanyProfile
    profiles = db.query(CompanyProfile).all()
    for profile in profiles:
        settings_str = profile.settings
        if settings_str and isinstance(settings_str, str):
            try:
                settings = json.loads(settings_str)
            except Exception:
                continue
            for inv_dict in settings.get("invitations", []):
                if inv_dict.get("inviteToken") == clean_token:
                    return {
                        "valid": True,
                        "email": inv_dict.get("email"),
                        "role": inv_dict.get("role"),
                        "company_name": profile.company_name,
                        "company_id": profile.id,
                        "token": clean_token,
                        "message": inv_dict.get("message", ""),
                        "status": inv_dict.get("status", "Pending"),
                    }

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found or expired")


@service_error_handler
def accept_team_invitation(
    db: Session,
    token: str,
    password: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    phone: Optional[str] = None,
) -> Tuple[CompanyUser, str]:
    """Accept invitation, set password, create active CompanyUser, and return session token."""
    clean_token = token.strip()
    inv = db.query(CompanyInvitation).filter(CompanyInvitation.invite_token == clean_token).first()

    company_id = None
    email = None
    role = "recruiter"
    invited_by_id = None

    if inv:
        if inv.status != "pending":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invitation has already been {inv.status.lower()}")
        company_id = inv.company_id
        email = inv.email.lower()
        role = inv.role
        invited_by_id = inv.invited_by_id
        inv.status = "accepted"
    else:
        # Check legacy JSON invitations
        profiles = db.query(CompanyProfile).all()
        found_profile = None
        for profile in profiles:
            settings_str = profile.settings
            if settings_str and isinstance(settings_str, str):
                try:
                    settings = json.loads(settings_str)
                except Exception:
                    continue
                invitations = settings.get("invitations", [])
                for i, inv_dict in enumerate(invitations):
                    if inv_dict.get("inviteToken") == clean_token:
                        found_profile = profile
                        email = inv_dict.get("email", "").lower()
                        role = inv_dict.get("role", "recruiter")
                        del settings["invitations"][i]
                        profile.settings = json.dumps(settings)
                        break
            if found_profile:
                company_id = found_profile.id
                break

    if not company_id or not email:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invitation token")

    # Find or create CompanyUser
    company_user = db.query(CompanyUser).filter(
        CompanyUser.email == email,
        CompanyUser.company_id == company_id,
        CompanyUser.is_deleted == False,
    ).first()

    if company_user:
        company_user.password_hash = hash_password(password)
        if first_name: company_user.first_name = first_name
        if last_name: company_user.last_name = last_name
        if phone: company_user.phone = phone
        company_user.role = role
        company_user.is_active = True
        company_user.is_verified = True
        company_user.last_login = datetime.now(timezone.utc)
    else:
        company_user = CompanyUser(
            company_id=company_id,
            email=email,
            password_hash=hash_password(password),
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role=role,
            is_active=True,
            is_verified=True,
            last_login=datetime.now(timezone.utc),
            invited_by_id=invited_by_id,
        )
        db.add(company_user)

    db.commit()
    db.refresh(company_user)

    access_token = create_company_token(
        user_id=company_user.id,
        company_id=company_user.company_id,
        email=company_user.email,
        role=company_user.role,
    )
    logger.info(f"Team member {company_user.email} activated for company {company_user.company_id}")
    return company_user, access_token


def get_invite_details(db: Session, token: str) -> Dict[str, Any]:
    """Compatibility wrapper for get_invite_details."""
    try:
        return verify_team_invitation(db, token)
    except HTTPException:
        return {"valid": False, "message": "Invitation not found or expired."}


def activate_invite_member(db: Session, token: str, name: str, password: str) -> Dict[str, Any]:
    """Compatibility wrapper for activate_invite_member."""
    parts = (name or "Team Member").strip().split(" ", 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ""

    cu, access_token = accept_team_invitation(
        db=db,
        token=token,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "name": cu.full_name,
        "user": {
            "id": cu.id,
            "email": cu.email,
            "full_name": cu.full_name,
            "company_id": cu.company_id,
            "role": cu.role,
        }
    }
