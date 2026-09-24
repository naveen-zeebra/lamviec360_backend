from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Callable
import jwt
from fastapi import Depends, HTTPException, status, Header
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
    roles: Optional[List[str]] = None,
    permissions: Optional[List[str]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=env.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "user_type": user_type,
        "roles": roles or [],
        "permissions": permissions or [],
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, env.JWT_SECRET_KEY, algorithm=env.JWT_ALGORITHM)


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


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Any:
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token missing or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = decode_token(auth.credentials)
    user_id = payload.get("sub")
    user_type = payload.get("user_type")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 1. If user_type is super_admin or admin, query AdminUser table first
    if user_type in ["super_admin", "admin"]:
        from shared.models.admin_user import AdminUser
        admin = db.query(AdminUser).filter(AdminUser.id == int(user_id), AdminUser.is_deleted == False).first()
        if admin:
            if not admin.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin account is deactivated",
                )
            return admin

    # 2. Check regular User table
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        # Fallback check AdminUser in case token user_type was omitted
        from shared.models.admin_user import AdminUser
        admin = db.query(AdminUser).filter(AdminUser.id == int(user_id), AdminUser.is_deleted == False).first()
        if admin:
            if not admin.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin account is deactivated",
                )
            return admin
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )
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
        user_type = payload.get("user_type")
        if not user_id:
            return None
        if user_type in ["super_admin", "admin"]:
            from shared.models.admin_user import AdminUser
            admin = db.query(AdminUser).filter(AdminUser.id == int(user_id), AdminUser.is_deleted == False).first()
            if admin and admin.is_active:
                return admin
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user and user.is_active:
            return user
        from shared.models.admin_user import AdminUser
        admin = db.query(AdminUser).filter(AdminUser.id == int(user_id), AdminUser.is_deleted == False).first()
        if admin and admin.is_active:
            return admin
        return None
    except Exception:
        return None


def require_user_type(*allowed_types: str) -> Callable:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.is_superuser:
            return user
        if user.user_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires one of {allowed_types} account",
            )
        return user
    return dependency


def require_roles(*allowed_roles: str) -> Callable:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.is_superuser or user.user_type == "super_admin":
            return user
        user_role_codes = [r.code for r in user.roles]
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

