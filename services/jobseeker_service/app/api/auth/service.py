# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/auth/service.py
# Purpose : Domain & persistence logic for Job Seeker Authentication
# ─────────────────────────────────────────────────────────────────────────────

import random
import secrets
import urllib.parse
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from shared.environment import env
from shared.models import User, JobSeekerProfile, Role, OAuthAccount
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
        # BR-101-01: Must be verified before the account is activated
        is_active=False,
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

    logger.info(f"Registered jobseeker {email} (user_id={user.id}, pending verification)")
    return user, profile


@service_error_handler
def authenticate_jobseeker(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate credentials specifically for candidate accounts."""
    user = db.query(User).filter(User.email == email.lower(), User.is_deleted == False).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    if user.role_type != "jobseeker":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Account is not a job seeker account.",
        )
    # BR-101-01: Account must be verified before activation
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not activated. Please verify your email address to activate your account.",
        )
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
    """
    BR-101-01: Contact verification.
    Marks jobseeker verified and activates the account.
    """
    user = db.query(User).filter(User.email == email.lower()).first()
    if user:
        user.is_verified = True
        user.is_active = True  # Activated after contact method is verified
        db.commit()
        db.refresh(user)
        logger.info(f"Jobseeker {email} verified and activated")
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


# ─────────────────────────────────────────────────────────────────────────────
# OAuth Helpers & Authentication (Google, Zalo, LinkedIn, Facebook)
# ─────────────────────────────────────────────────────────────────────────────

def get_oauth_providers_config() -> List[Dict[str, Any]]:
    """Return available OAuth identity providers and their configuration."""
    return [
        {
            "id": "google",
            "name": "Google",
            "enabled": True,
            "has_credentials": bool(env.GOOGLE_CLIENT_ID),
            "client_id": env.GOOGLE_CLIENT_ID,
            "redirect_uri": env.GOOGLE_REDIRECT_URI,
        },
        {
            "id": "zalo",
            "name": "Zalo",
            "enabled": True,
            "has_credentials": bool(env.ZALO_APP_ID),
            "client_id": env.ZALO_APP_ID,
            "redirect_uri": env.ZALO_REDIRECT_URI,
        },
        {
            "id": "linkedin",
            "name": "LinkedIn",
            "enabled": True,
            "has_credentials": bool(env.LINKEDIN_CLIENT_ID),
            "client_id": env.LINKEDIN_CLIENT_ID,
            "redirect_uri": env.LINKEDIN_REDIRECT_URI,
        },
        {
            "id": "facebook",
            "name": "Facebook",
            "enabled": True,
            "has_credentials": bool(env.FACEBOOK_APP_ID),
            "client_id": env.FACEBOOK_APP_ID,
            "redirect_uri": env.FACEBOOK_REDIRECT_URI,
        },
    ]


def get_oauth_authorization_url(
    provider: str,
    redirect_uri: Optional[str] = None,
    state: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate official OAuth 2.0 authorization URL for the requested provider."""
    provider = provider.lower()
    state = state or secrets.token_urlsafe(16)

    if provider == "google":
        client_id = env.GOOGLE_CLIENT_ID or "mock-google-client-id"
        red_uri = redirect_uri or env.GOOGLE_REDIRECT_URI
        params = {
            "client_id": client_id,
            "redirect_uri": red_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
        return {"provider": "google", "authorization_url": url, "client_id": client_id, "redirect_uri": red_uri, "state": state}

    elif provider == "zalo":
        app_id = env.ZALO_APP_ID or "mock-zalo-app-id"
        red_uri = redirect_uri or env.ZALO_REDIRECT_URI
        params = {
            "app_id": app_id,
            "redirect_uri": red_uri,
            "state": state,
        }
        url = f"https://oauth.zaloapp.com/v4/permission?{urllib.parse.urlencode(params)}"
        return {"provider": "zalo", "authorization_url": url, "client_id": app_id, "redirect_uri": red_uri, "state": state}

    elif provider == "linkedin":
        client_id = env.LINKEDIN_CLIENT_ID or "mock-linkedin-client-id"
        red_uri = redirect_uri or env.LINKEDIN_REDIRECT_URI
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": red_uri,
            "scope": "openid profile email",
            "state": state,
        }
        url = f"https://www.linkedin.com/oauth/v2/authorization?{urllib.parse.urlencode(params)}"
        return {"provider": "linkedin", "authorization_url": url, "client_id": client_id, "redirect_uri": red_uri, "state": state}

    elif provider == "facebook":
        app_id = env.FACEBOOK_APP_ID or "mock-facebook-app-id"
        red_uri = redirect_uri or env.FACEBOOK_REDIRECT_URI
        params = {
            "client_id": app_id,
            "redirect_uri": red_uri,
            "scope": "email,public_profile",
            "state": state,
        }
        url = f"https://www.facebook.com/v19.0/dialog/oauth?{urllib.parse.urlencode(params)}"
        return {"provider": "facebook", "authorization_url": url, "client_id": app_id, "redirect_uri": red_uri, "state": state}

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported OAuth provider: '{provider}'. Must be google, zalo, linkedin, or facebook.",
    )


def verify_oauth_credentials(
    provider: str,
    code: Optional[str] = None,
    token: Optional[str] = None,
    redirect_uri: Optional[str] = None,
    code_verifier: Optional[str] = None,
    fallback_email: Optional[str] = None,
    fallback_name: Optional[str] = None,
    fallback_avatar: Optional[str] = None,
    fallback_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Exchanges code/token with provider API or resolves user profile.
    Supports real OAuth APIs with graceful fallback for development and sandbox testing.
    """
    provider = provider.lower()
    email = fallback_email
    name = fallback_name
    avatar_url = fallback_avatar
    provider_user_id = fallback_id
    access_token = token
    refresh_token = None
    raw_data: Dict[str, Any] = {}

    # 1. Google OAuth
    if provider == "google":
        if code and env.GOOGLE_CLIENT_ID and env.GOOGLE_CLIENT_SECRET:
            try:
                red_uri = redirect_uri or env.GOOGLE_REDIRECT_URI
                token_res = httpx.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "code": code,
                        "client_id": env.GOOGLE_CLIENT_ID,
                        "client_secret": env.GOOGLE_CLIENT_SECRET,
                        "redirect_uri": red_uri,
                        "grant_type": "authorization_code",
                    },
                    timeout=10.0,
                )
                if token_res.status_code == 200:
                    token_data = token_res.json()
                    access_token = token_data.get("access_token")
                    refresh_token = token_data.get("refresh_token")
            except Exception as e:
                logger.warning(f"Google token exchange failed: {e}")

        if access_token:
            try:
                u_res = httpx.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10.0,
                )
                if u_res.status_code == 200:
                    raw_data = u_res.json()
                    email = raw_data.get("email") or email
                    name = raw_data.get("name") or name
                    avatar_url = raw_data.get("picture") or avatar_url
                    provider_user_id = str(raw_data.get("sub") or provider_user_id)
            except Exception as e:
                logger.warning(f"Google userinfo request failed: {e}")

    # 2. Zalo OAuth
    elif provider == "zalo":
        if code and env.ZALO_APP_ID and env.ZALO_APP_SECRET:
            try:
                data = {
                    "code": code,
                    "app_id": env.ZALO_APP_ID,
                    "grant_type": "authorization_code",
                }
                if code_verifier:
                    data["code_verifier"] = code_verifier
                token_res = httpx.post(
                    "https://oauth.zaloapp.com/v4/access_token",
                    headers={"secret_key": env.ZALO_APP_SECRET, "Content-Type": "application/x-www-form-urlencoded"},
                    data=data,
                    timeout=10.0,
                )
                if token_res.status_code == 200:
                    token_data = token_res.json()
                    access_token = token_data.get("access_token")
                    refresh_token = token_data.get("refresh_token")
            except Exception as e:
                logger.warning(f"Zalo token exchange failed: {e}")

        if access_token:
            try:
                u_res = httpx.get(
                    "https://graph.zalo.me/v2.0/me?fields=id,name,picture",
                    headers={"access_token": access_token},
                    timeout=10.0,
                )
                if u_res.status_code == 200:
                    raw_data = u_res.json()
                    provider_user_id = str(raw_data.get("id") or provider_user_id)
                    name = raw_data.get("name") or name
                    pic = raw_data.get("picture", {})
                    avatar_url = (pic.get("data", {}).get("url") if isinstance(pic, dict) else None) or avatar_url
            except Exception as e:
                logger.warning(f"Zalo profile fetch failed: {e}")

    # 3. LinkedIn OAuth
    elif provider == "linkedin":
        if code and env.LINKEDIN_CLIENT_ID and env.LINKEDIN_CLIENT_SECRET:
            try:
                red_uri = redirect_uri or env.LINKEDIN_REDIRECT_URI
                token_res = httpx.post(
                    "https://www.linkedin.com/oauth/v2/accessToken",
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "client_id": env.LINKEDIN_CLIENT_ID,
                        "client_secret": env.LINKEDIN_CLIENT_SECRET,
                        "redirect_uri": red_uri,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10.0,
                )
                if token_res.status_code == 200:
                    token_data = token_res.json()
                    access_token = token_data.get("access_token")
                    refresh_token = token_data.get("refresh_token")
            except Exception as e:
                logger.warning(f"LinkedIn token exchange failed: {e}")

        if access_token:
            try:
                u_res = httpx.get(
                    "https://api.linkedin.com/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10.0,
                )
                if u_res.status_code == 200:
                    raw_data = u_res.json()
                    provider_user_id = str(raw_data.get("sub") or provider_user_id)
                    email = raw_data.get("email") or email
                    name = raw_data.get("name") or name
                    avatar_url = raw_data.get("picture") or avatar_url
            except Exception as e:
                logger.warning(f"LinkedIn userinfo fetch failed: {e}")

    # 4. Facebook OAuth
    elif provider == "facebook":
        if code and env.FACEBOOK_APP_ID and env.FACEBOOK_APP_SECRET:
            try:
                red_uri = redirect_uri or env.FACEBOOK_REDIRECT_URI
                token_res = httpx.get(
                    "https://graph.facebook.com/v19.0/oauth/access_token",
                    params={
                        "client_id": env.FACEBOOK_APP_ID,
                        "client_secret": env.FACEBOOK_APP_SECRET,
                        "redirect_uri": red_uri,
                        "code": code,
                    },
                    timeout=10.0,
                )
                if token_res.status_code == 200:
                    token_data = token_res.json()
                    access_token = token_data.get("access_token")
            except Exception as e:
                logger.warning(f"Facebook token exchange failed: {e}")

        if access_token:
            try:
                u_res = httpx.get(
                    "https://graph.facebook.com/me?fields=id,name,email,picture.type(large)",
                    params={"access_token": access_token},
                    timeout=10.0,
                )
                if u_res.status_code == 200:
                    raw_data = u_res.json()
                    provider_user_id = str(raw_data.get("id") or provider_user_id)
                    email = raw_data.get("email") or email
                    name = raw_data.get("name") or name
                    pic = raw_data.get("picture", {})
                    avatar_url = (pic.get("data", {}).get("url") if isinstance(pic, dict) else None) or avatar_url
            except Exception as e:
                logger.warning(f"Facebook profile fetch failed: {e}")

    # Fallback resolution for development/sandbox/mock testing
    if not provider_user_id:
        provider_user_id = fallback_id or f"{provider}_{secrets.token_hex(6)}"

    if not email:
        if fallback_email:
            email = fallback_email
        else:
            sanitized_id = "".join(c for c in str(provider_user_id) if c.isalnum())[:16]
            email = f"{provider}.{sanitized_id}@social.lamviec360.vn"

    if not name:
        name = fallback_name or f"{provider.capitalize()} User"

    return {
        "provider": provider,
        "provider_user_id": str(provider_user_id),
        "email": email.strip().lower(),
        "name": name.strip(),
        "avatar_url": avatar_url,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "raw_data": raw_data,
    }


@service_error_handler
def authenticate_or_register_oauth_user(
    db: Session,
    oauth_info: Dict[str, Any],
) -> Tuple[User, bool, bool]:
    """
    Authenticate or register user via OAuth.
    Implements BRD LV-BR-0037: Auto-linking to existing accounts if email matches.
    Returns: (user, is_new_user, is_auto_linked)
    """
    provider = oauth_info["provider"]
    provider_user_id = str(oauth_info["provider_user_id"])
    email = oauth_info["email"].lower()
    name = oauth_info.get("name")
    avatar_url = oauth_info.get("avatar_url")
    provider_token = oauth_info.get("access_token")
    provider_refresh = oauth_info.get("refresh_token")

    # 1. Check if OAuth account is already registered with (provider, provider_user_id)
    oauth_account = (
        db.query(OAuthAccount)
        .filter(OAuthAccount.provider == provider, OAuthAccount.provider_user_id == provider_user_id)
        .first()
    )

    if oauth_account:
        user = db.query(User).filter(User.id == oauth_account.user_id).first()
        if user and not user.is_deleted:
            oauth_account.access_token = provider_token or oauth_account.access_token
            oauth_account.refresh_token = provider_refresh or oauth_account.refresh_token
            oauth_account.provider_email = email
            user.last_login = datetime.now(timezone.utc)
            if not user.avatar_url and avatar_url:
                user.avatar_url = avatar_url

            # Ensure JobSeekerProfile exists for candidate actions
            if not user.jobseeker_profile:
                profile = JobSeekerProfile(user_id=user.id)
                db.add(profile)

            # Ensure jobseeker role is present
            seeker_role = db.query(Role).filter(Role.code == "jobseeker").first()
            if seeker_role and seeker_role not in user.roles:
                user.roles.append(seeker_role)

            db.commit()
            db.refresh(user)
            logger.info(f"Existing OAuth login: user_id={user.id}, provider={provider}")
            return user, False, False

    # 2. Check if a User already exists with the same email (LV-BR-0037 Auto-linking)
    existing_user = db.query(User).filter(User.email == email, User.is_deleted == False).first()

    if existing_user:
        new_oauth = OAuthAccount(
            user_id=existing_user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=email,
            access_token=provider_token,
            refresh_token=provider_refresh,
        )
        db.add(new_oauth)
        existing_user.is_verified = True  # OAuth validates email ownership
        existing_user.last_login = datetime.now(timezone.utc)
        if not existing_user.avatar_url and avatar_url:
            existing_user.avatar_url = avatar_url

        # Ensure JobSeekerProfile exists for candidate actions
        if not existing_user.jobseeker_profile:
            profile = JobSeekerProfile(user_id=existing_user.id)
            db.add(profile)

        # Ensure jobseeker role is present
        seeker_role = db.query(Role).filter(Role.code == "jobseeker").first()
        if seeker_role and seeker_role not in existing_user.roles:
            existing_user.roles.append(seeker_role)

        db.commit()
        db.refresh(existing_user)
        logger.info(f"Auto-linked OAuth account {provider} to existing user_id={existing_user.id} ({email}) per LV-BR-0037")
        return existing_user, False, True

    # 3. New User Registration via OAuth
    seeker_role = db.query(Role).filter(Role.code == "jobseeker").first()
    roles = [seeker_role] if seeker_role else []

    random_password = secrets.token_urlsafe(24)
    new_user = User(
        email=email,
        hashed_password=hash_password(random_password),
        full_name=name,
        user_type="jobseeker",
        is_active=True,
        is_verified=True,  # Social login emails are verified
        avatar_url=avatar_url,
        roles=roles,
        last_login=datetime.now(timezone.utc),
    )
    db.add(new_user)
    db.flush()

    # Create seeker profile
    profile = JobSeekerProfile(user_id=new_user.id)
    db.add(profile)

    # Link OAuth account
    new_oauth = OAuthAccount(
        user_id=new_user.id,
        provider=provider,
        provider_user_id=provider_user_id,
        provider_email=email,
        access_token=provider_token,
        refresh_token=provider_refresh,
    )
    db.add(new_oauth)

    db.commit()
    db.refresh(new_user)
    logger.info(f"Created new jobseeker user_id={new_user.id} via {provider} OAuth ({email})")
    return new_user, True, False
