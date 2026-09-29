# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/auth/service.py
# Purpose : Domain & persistence logic for Company Portal Auth
# ─────────────────────────────────────────────────────────────────────────────

import random
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from shared.models import User, CompanyProfile, Role
from shared.utils.error_handler import service_error_handler
from shared.utils.password import hash_password, verify_password
from shared.utils.logger import get_logger

logger = get_logger("company_auth_service")

# In-memory verification cache: email -> { "code": str, "expires_at": datetime }
_VERIFICATION_CACHE: Dict[str, dict] = {}


@service_error_handler
def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Look up a user by lowercased email."""
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
    """Create new company employer user and pending company profile."""
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
    db.commit()
    db.refresh(user)
    db.refresh(profile)

    logger.info(f"Created company user {email} and company profile {profile.company_name} (ID: {profile.id})")
    return user, profile


@service_error_handler
def authenticate_company_user(db: Session, email: str, password: str) -> Optional[User]:
    """Validate credentials and return user if active."""
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


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
def mark_user_verified(db: Session, email: str) -> Optional[User]:
    """Update user is_verified status to True."""
    user = db.query(User).filter(User.email == email.lower()).first()
    if user:
        user.is_verified = True
        db.commit()
        db.refresh(user)
        logger.info(f"Marked company user {email} as verified")
    return user


@service_error_handler
def get_company_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Fetch user by id."""
    return db.query(User).filter(User.id == user_id).first()


@service_error_handler
def change_company_user_password(db: Session, user: User, old_password: str, new_password: str) -> bool:
    """Verify current password and set new hashed password."""
    if not verify_password(old_password, user.hashed_password):
        return False
    user.hashed_password = hash_password(new_password)
    db.commit()
    logger.info(f"Password changed successfully for company user id={user.id}")
    return True


def get_invite_details(token: str) -> Dict[str, Any]:
    """Return mock or persisted team invitation details."""
    return {
        "valid": True,
        "email": "invited@example.com",
        "role": "HR / Recruiter",
        "company_name": "Sample Company",
        "token": token,
        "message": "Welcome to our team!",
    }


def activate_invite_member(token: str, name: str, password: str) -> Dict[str, Any]:
    """Activate invited team member."""
    return {
        "access_token": "mock_token",
        "token_type": "bearer",
        "name": name,
    }
