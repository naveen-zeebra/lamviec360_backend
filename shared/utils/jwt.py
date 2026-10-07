from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Callable
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from shared.environment import env
from shared.database.session import get_db
from shared.models.user import User

security = HTTPBearer(auto_error=False)

def create_access_token(
    user_id: int,
    email: str,
    user_type: str,
    system: Optional[str] = None,
    roles: Optional[List[str]] = None,
    permissions: Optional[List[str]] = None,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=env.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Infer system if not explicitly provided
    if not system:
        if user_type in ["super_admin", "admin"]:
            system = "super_admin"
        elif user_type in ["company", "company_admin", "recruiter", "hiring_manager", "interviewer"]:
            system = "company"
        else:
            system = "jobseeker"

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "system": system,
        "user_type": user_type,
        "roles": roles or [],
        "permissions": permissions or [],
        "exp": expire,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, env.JWT_SECRET_KEY, algorithm=env.JWT_ALGORITHM)


def create_admin_token(
    admin_id: int,
    email: str,
    role_code: str = "super_admin",
    permissions: Optional[List[str]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generate JWT specifically for Super Admin Gateway with system=super_admin."""
    return create_access_token(
        user_id=admin_id,
        email=email,
        user_type="super_admin",
        system="super_admin",
        roles=[role_code],
        permissions=permissions or [],
        expires_delta=expires_delta,
    )


def create_company_token(
    user_id: int,
    company_id: int,
    email: str,
    role: str = "recruiter",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generate JWT specifically for Company Gateway with system=company and company_id."""
    return create_access_token(
        user_id=user_id,
        email=email,
        user_type="company",
        system="company",
        roles=[role],
        expires_delta=expires_delta,
        extra_claims={"company_id": company_id, "role": role},
    )


def create_jobseeker_token(
    seeker_id: int,
    email: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generate JWT specifically for Job Seeker Gateway with system=jobseeker."""
    return create_access_token(
        user_id=seeker_id,
        email=email,
        user_type="jobseeker",
        system="jobseeker",
        roles=["jobseeker"],
        expires_delta=expires_delta,
    )


def create_refresh_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=env.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, env.JWT_SECRET_KEY, algorithm=env.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, env.JWT_SECRET_KEY, algorithms=[env.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _extract_token_payload(auth: Optional[HTTPAuthorizationCredentials]) -> Dict[str, Any]:
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token missing or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(auth.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def get_current_admin(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Any:
    """Authentication guard for Super Admin Gateway. Enforces system=super_admin."""
    payload = _extract_token_payload(auth)
    system = payload.get("system")
    user_type = payload.get("user_type")
    if system and system != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token system for Admin Gateway: expected super_admin",
        )
    if not system and user_type not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token system for Admin Gateway: expected super_admin",
        )

    user_id = int(payload.get("sub"))
    from shared.models.admin_user import AdminUser
    admin = db.query(AdminUser).filter(AdminUser.id == user_id, AdminUser.is_deleted == False).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin account not found")
    if not admin.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin account is deactivated")
    return admin


def get_current_company_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Any:
    """Authentication guard for Company Gateway. Enforces system=company."""
    payload = _extract_token_payload(auth)
    system = payload.get("system")
    user_type = payload.get("user_type")
    if system and system != "company":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token system for Company Gateway: expected company",
        )
    if not system and user_type != "company":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token system for Company Gateway: expected company",
        )

    user_id = int(payload.get("sub"))
    from shared.models.company_user import CompanyUser
    company_user = db.query(CompanyUser).filter(CompanyUser.id == user_id, CompanyUser.is_deleted == False).first()
    if company_user:
        if not company_user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company team member account is deactivated")
        return company_user

    # Fallback to User table for legacy company account
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if user and user.user_type == "company":
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company account is deactivated")
        return user

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company user not found")


def get_current_jobseeker(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Authentication guard for Job Seeker Gateway. Enforces system=jobseeker."""
    payload = _extract_token_payload(auth)
    system = payload.get("system")
    user_type = payload.get("user_type")
    if system and system != "jobseeker":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token system for Job Seeker Gateway: expected jobseeker",
        )
    if not system and user_type != "jobseeker":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token system for Job Seeker Gateway: expected jobseeker",
        )

    user_id = int(payload.get("sub"))
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job seeker account not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Job seeker account is deactivated")

    has_seeker_role = any(r.code == "jobseeker" for r in user.roles)
    if user.role_type != "jobseeker" and not has_seeker_role and not user.jobseeker_profile:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a job seeker account")

    if not user.jobseeker_profile:
        from shared.models.jobseeker import JobSeekerProfile
        profile = JobSeekerProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(user)

    return user


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Any:
    """Unified user resolver for backward compatibility across endpoints."""
    payload = _extract_token_payload(auth)
    system = payload.get("system")
    user_type = payload.get("user_type")
    user_id = int(payload.get("sub"))

    if system == "super_admin" or user_type in ["super_admin", "admin"]:
        from shared.models.admin_user import AdminUser
        admin = db.query(AdminUser).filter(AdminUser.id == user_id, AdminUser.is_deleted == False).first()
        if admin:
            if not admin.is_active:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin account is deactivated")
            return admin

    if system == "company" or user_type == "company":
        from shared.models.company_user import CompanyUser
        co_user = db.query(CompanyUser).filter(CompanyUser.id == user_id, CompanyUser.is_deleted == False).first()
        if co_user:
            if not co_user.is_active:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company team member is deactivated")
            return co_user

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        from shared.models.admin_user import AdminUser
        admin = db.query(AdminUser).filter(AdminUser.id == user_id, AdminUser.is_deleted == False).first()
        if admin:
            if not admin.is_active:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin account is deactivated")
            return admin
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated")
    return user


def get_current_active_user_optional(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[Any]:
    if not auth or not auth.credentials:
        return None
    try:
        payload = decode_token(auth.credentials)
        user_id = payload.get("sub")
        if not user_id:
            return None
        user_id_int = int(user_id)
        system = payload.get("system")
        user_type = payload.get("user_type")

        if system == "super_admin" or user_type in ["super_admin", "admin"]:
            from shared.models.admin_user import AdminUser
            admin = db.query(AdminUser).filter(AdminUser.id == user_id_int, AdminUser.is_deleted == False).first()
            if admin and admin.is_active:
                return admin

        if system == "company" or user_type == "company":
            from shared.models.company_user import CompanyUser
            co_user = db.query(CompanyUser).filter(CompanyUser.id == user_id_int, CompanyUser.is_deleted == False).first()
            if co_user and co_user.is_active:
                return co_user

        user = db.query(User).filter(User.id == user_id_int).first()
        if user and user.is_active:
            return user
        return None
    except Exception:
        return None


def require_user_type(*allowed_types: str) -> Callable:
    def dependency(user: Any = Depends(get_current_user)) -> Any:
        if getattr(user, "is_superuser", False):
            return user
        u_type = getattr(user, "user_type", None) or getattr(user, "role_type", None)
        if u_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires one of {allowed_types} account",
            )
        return user
    return dependency


def require_roles(*allowed_roles: str) -> Callable:
    def dependency(user: Any = Depends(get_current_admin)) -> Any:
        if getattr(user, "is_superuser", False):
            return user
        u_type = getattr(user, "user_type", None)
        if u_type == "super_admin":
            return user
        role_code = getattr(user, "role_name", None) or getattr(user, "role", None)
        if isinstance(role_code, str):
            role_code = role_code.lower().replace(" ", "_")
        roles = getattr(user, "roles", [])
        user_role_codes = [getattr(r, "code", r).lower() for r in roles]
        if role_code:
            user_role_codes.append(role_code)
        if "super_admin" in user_role_codes:
            return user
        if not any(role in user_role_codes for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this operation",
            )
        return user
    return dependency


def create_password_reset_token(
    user_id: int,
    email: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=1)
    
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "type": "password_reset",
        "exp": expire,
    }
    return jwt.encode(payload, env.JWT_SECRET_KEY, algorithm=env.JWT_ALGORITHM)
