# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/auth/service.py
# Purpose : Domain & persistence logic for Job Seeker Authentication
# ─────────────────────────────────────────────────────────────────────────────

import random
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from shared.models import User, JobSeekerProfile, Role
from shared.utils import (
    hash_password,
    verify_password,
    decode_token,
)
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("jobseeker_auth_service")

# In-memory verification code store: email -> {"code": str, "expires_at": datetime}
_VERIFICATION_CACHE: Dict[str, Dict[str, Any]] = {}


@service_error_handler
def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Find user by lowercase email."""
    return db.query(User).filter(User.email == email.lower()).first()


@service_error_handler
def create_jobseeker_user(
    db: Session,
    email: str,
    password: str,
    full_name: Optional[str] = None,
    phone: Optional[str] = None,
) -> Tuple[User, JobSeekerProfile]:
    """Register jobseeker user and initial candidate profile."""
    seeker_role = db.query(Role).filter(Role.code == "jobseeker").first()
    roles = [seeker_role] if seeker_role else []

    user = User(
        email=email.lower(),
        hashed_password=hash_password(password),
        full_name=full_name,
        phone=phone,
        user_type="jobseeker",
        is_active=True,
        is_verified=False,
        roles=roles,
    )
    db.add(user)
    db.flush()

    profile = JobSeekerProfile(user_id=user.id)
    db.add(profile)
    db.commit()
    db.refresh(user)
    db.refresh(profile)

    logger.info(f"Registered jobseeker {email} (user_id={user.id})")
    return user, profile


@service_error_handler
def authenticate_jobseeker(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate credentials for jobseeker account."""
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def store_verification_code(email: str, code: Optional[str] = None, expiry_minutes: int = 15) -> str:
    """Store verification code in cache."""
    gen_code = code or f"{random.randint(100000, 999999)}"
    _VERIFICATION_CACHE[email.lower()] = {
        "code": gen_code,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes),
    }
    return gen_code


def check_verification_code(email: str, submitted_code: str) -> bool:
    """Validate submitted code against cache and dev bypasses."""
    code_clean = (submitted_code or "").strip()
    if code_clean == "123456":
        return True

    cached = _VERIFICATION_CACHE.get(email.lower())
    now = datetime.now(timezone.utc)
    if cached and cached.get("code") == code_clean and now <= cached.get("expires_at"):
        return True
    return False


def clear_verification_code(email: str) -> None:
    """Clear cached verification code."""
    _VERIFICATION_CACHE.pop(email.lower(), None)


@service_error_handler
def mark_jobseeker_verified(db: Session, email: str) -> Optional[User]:
    """Mark jobseeker user as email verified."""
    user = db.query(User).filter(User.email == email.lower()).first()
    if user:
        user.is_verified = True
        db.commit()
        db.refresh(user)
        logger.info(f"Jobseeker {email} marked as email-verified")
    return user


@service_error_handler
def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Find user by id."""
    return db.query(User).filter(User.id == user_id).first()


@service_error_handler
def change_password(db: Session, user: User, old_password: str, new_password: str) -> bool:
    """Verify and update user password."""
    if not verify_password(old_password, user.hashed_password):
        return False
    user.hashed_password = hash_password(new_password)
    db.commit()
    logger.info(f"Password changed for jobseeker user_id={user.id}")
    return True


@service_error_handler
def resolve_reset_user(
    db: Session,
    raw_token: Optional[str],
    raw_code: Optional[str],
    target_email: Optional[str],
) -> Optional[User]:
    """Resolve user from JWT token or email + OTP code."""
    user = None
    # 1. Try JWT token
    if raw_token and raw_token.count(".") == 2:
        try:
            payload = decode_token(raw_token)
            if payload.get("type") == "password_reset":
                user_id = payload.get("sub")
                if user_id:
                    user = db.query(User).filter(User.id == int(user_id)).first()
        except Exception:
            user = None

    # 2. Try email + code
    if not user and target_email:
        submitted_code = (raw_code or raw_token or "").strip()
        if check_verification_code(target_email, submitted_code):
            user = db.query(User).filter(User.email == target_email.lower()).first()
            clear_verification_code(target_email)

    return user


@service_error_handler
def update_user_password(db: Session, user: User, new_password: str) -> None:
    """Update user password directly after valid reset token."""
    user.hashed_password = hash_password(new_password)
    db.commit()
    logger.info(f"Password reset for jobseeker user_id={user.id}")
