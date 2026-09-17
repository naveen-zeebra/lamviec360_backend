from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.user import User
from app.models.enums import UserRole
from app.schemas.auth_admin import AdminLoginRequest, AdminTokenResponse
from app.api.deps import get_current_super_admin

router = APIRouter(prefix="/auth/admin", tags=["Auth - Super Admin"])


@router.post("/login", response_model=AdminTokenResponse)
def login_super_admin(req: AdminLoginRequest, db: Session = Depends(get_db)):
    """Authenticates a platform Super Admin and issues an administrative JWT."""
    user = db.query(User).filter(User.email == req.email.lower()).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect Super Admin credentials.",
        )

    if user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account does not have Super Admin platform privileges.",
        )

    user.last_login_at = datetime.utcnow()
    db.commit()

    token = create_access_token(subject=user.id, role=user.role.value)
    return AdminTokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role.value,
        user_id=user.id,
        name=user.name,
        email=user.email,
    )


@router.get("/me", response_model=AdminTokenResponse)
def get_current_admin(current_user: User = Depends(get_current_super_admin)):
    """Returns current Super Admin session details."""
    return AdminTokenResponse(
        access_token="",
        token_type="bearer",
        role=current_user.role.value,
        user_id=current_user.id,
        name=current_user.name,
        email=current_user.email,
    )
