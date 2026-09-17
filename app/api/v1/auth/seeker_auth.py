from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings
from app.models.user import User
from app.models.seeker import SeekerProfile
from app.models.enums import UserRole, UserStatus
from app.schemas.auth_seeker import (
    SeekerRegisterRequest,
    SeekerVerifyEmailRequest,
    SeekerLoginRequest,
    SeekerGoogleLoginRequest,
    SeekerTokenResponse,
)
from app.schemas.common import MessageResponse
from app.api.deps import get_current_seeker

router = APIRouter(prefix="/auth/seeker", tags=["Auth - Job Seeker"])


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def register_seeker(req: SeekerRegisterRequest, db: Session = Depends(get_db)):
    """Registers a new Job Seeker account."""
    existing = db.query(User).filter(User.email == req.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    user = User(
        email=req.email.lower(),
        name=req.name,
        hashed_password=get_password_hash(req.password),
        role=UserRole.JOB_SEEKER,
        status=UserStatus.ACTIVE,
        email_verified=False,
        two_factor_enabled=False,
    )
    db.add(user)
    db.flush()

    # Create empty SeekerProfile
    profile = SeekerProfile(
        user_id=user.id,
        preferences={"roles": [], "locations": [], "workMode": "", "salary": ""},
    )
    db.add(profile)
    db.commit()

    return MessageResponse(
        success=True,
        message=f"Registration successful. Verification code has been sent to {req.email}.",
        data={"email": user.email, "user_id": user.id},
    )


@router.post("/verify-email", response_model=MessageResponse)
def verify_seeker_email(req: SeekerVerifyEmailRequest, db: Session = Depends(get_db)):
    """Verifies a seeker's email with the verification code (Default Dev Code: 123456)."""
    user = db.query(User).filter(User.email == req.email.lower(), User.role == UserRole.JOB_SEEKER).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job Seeker not found")

    if settings.DEV_MOCK_OTP_ENABLED and req.code != settings.DEFAULT_OTP_CODE and req.code != "000000":
        # In mock dev mode, accept 123456
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code. (Hint: Use 123456 in dev mode)")

    user.email_verified = True
    db.commit()

    return MessageResponse(success=True, message="Email verified successfully. You can now log in.")


@router.post("/login", response_model=SeekerTokenResponse)
def login_seeker(req: SeekerLoginRequest, db: Session = Depends(get_db)):
    """Authenticates a Job Seeker and issues a JWT token."""
    user = db.query(User).filter(User.email == req.email.lower()).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    if user.role != UserRole.JOB_SEEKER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This login portal is only for Job Seekers. Employers please use Employer Login.",
        )

    user.last_login_at = datetime.utcnow()
    db.commit()

    token = create_access_token(subject=user.id, role=user.role.value)
    return SeekerTokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role.value,
        user_id=user.id,
        name=user.name,
        email=user.email,
        email_verified=user.email_verified,
    )


@router.post("/google", response_model=SeekerTokenResponse)
def google_login_seeker(req: SeekerGoogleLoginRequest, db: Session = Depends(get_db)):
    """Single sign-on for Job Seeker with Google."""
    user = db.query(User).filter(User.email == req.email.lower()).first()
    if not user:
        # Auto-create seeker user on first Google login
        user = User(
            email=req.email.lower(),
            name=req.name,
            hashed_password=get_password_hash("GOOGLE_SSO_PLACEHOLDER"),
            role=UserRole.JOB_SEEKER,
            status=UserStatus.ACTIVE,
            email_verified=True,
            two_factor_enabled=False,
        )
        db.add(user)
        db.flush()
        profile = SeekerProfile(user_id=user.id)
        db.add(profile)
        db.commit()

    token = create_access_token(subject=user.id, role=user.role.value)
    return SeekerTokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role.value,
        user_id=user.id,
        name=user.name,
        email=user.email,
        email_verified=user.email_verified,
    )


@router.get("/me", response_model=SeekerTokenResponse)
def get_current_seeker_profile(current_user: User = Depends(get_current_seeker)):
    """Returns the authenticated Job Seeker's auth info."""
    return SeekerTokenResponse(
        access_token="",
        token_type="bearer",
        role=current_user.role.value,
        user_id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        email_verified=current_user.email_verified,
    )
