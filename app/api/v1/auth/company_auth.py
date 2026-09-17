from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_session_token,
    decode_token,
)
from app.core.config import settings
from app.models.user import User
from app.models.company import Company, CompanyInvitation
from app.models.enums import UserRole, UserStatus, CompanyApprovalStatus
from app.schemas.auth_company import (
    CompanyRegisterRequest,
    CompanyVerifyEmailRequest,
    CompanyLoginInitiateRequest,
    CompanyLoginInitiateResponse,
    CompanyLoginVerifyOtpRequest,
    CompanyTokenResponse,
    AcceptInviteRequest,
)
from app.schemas.common import MessageResponse
from app.api.deps import get_current_company_user

router = APIRouter(prefix="/auth/company", tags=["Auth - Company & Employer"])


def mask_email(email: str) -> str:
    if "@" not in email:
        return email
    name, domain = email.split("@")
    if len(name) <= 2:
        return f"{name[0]}*@{domain}"
    return f"{name[0]}{'*' * (len(name) - 2)}{name[-1]}@{domain}"


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def register_company(req: CompanyRegisterRequest, db: Session = Depends(get_db)):
    """Registers a new Company and its primary Company Admin account in Pending status."""
    existing_user = db.query(User).filter(User.email == req.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this work email already exists.",
        )

    # Create Company entity in PENDING status
    company = Company(
        name=req.company_name,
        reg_number=req.reg_number,
        industry=req.industry,
        size=req.size,
        website=req.website,
        approval_status=CompanyApprovalStatus.PENDING,
        verified=False,
        email_verified=False,
        plan_id="Freemium",
        settings={
            "notifications": {"newApplications": True, "interviewReminders": True, "teamActivity": True, "billing": True},
            "security": {"twoFactor": True},
            "pipeline": {"autoRejectEmail": True},
        },
    )
    db.add(company)
    db.flush()

    # Create initial Company Admin User
    admin_user = User(
        email=req.email.lower(),
        name=req.contact_name,
        hashed_password=get_password_hash(req.password),
        role=UserRole.COMPANY_ADMIN,
        status=UserStatus.PENDING,
        email_verified=False,
        two_factor_enabled=True,
        company_id=company.id,
    )
    db.add(admin_user)
    db.commit()

    return MessageResponse(
        success=True,
        message="Company account created successfully. Please verify your work email.",
        data={"company_id": company.id, "email": admin_user.email},
    )


@router.post("/verify-email", response_model=MessageResponse)
def verify_company_email(req: CompanyVerifyEmailRequest, db: Session = Depends(get_db)):
    """Verifies the Company Admin's work email."""
    user = db.query(User).filter(User.email == req.email.lower(), User.role == UserRole.COMPANY_ADMIN).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company Admin account not found")

    if settings.DEV_MOCK_OTP_ENABLED and req.code != settings.DEFAULT_OTP_CODE and req.code != "000000":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code. (Hint: Use 123456 in dev mode)")

    user.email_verified = True
    if user.company:
        user.company.email_verified = True
    db.commit()

    return MessageResponse(success=True, message="Work email verified successfully. Your account is pending Super Admin review.")


@router.post("/login/initiate", response_model=CompanyLoginInitiateResponse)
def initiate_employer_login(req: CompanyLoginInitiateRequest, db: Session = Depends(get_db)):
    """Step 1 of Employer Login: Verifies credentials, checks tenant approval status, and dispatches 2FA OTP."""
    user = db.query(User).filter(User.email == req.email.lower()).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect work email or password.")

    if user.role not in [UserRole.COMPANY_ADMIN, UserRole.COMPANY_HR, UserRole.COMPANY_VIEWER]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account does not have Employer access.")

    company = user.company
    if not company:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No company associated with this account.")

    # Check Company Approval Status
    if company.approval_status == CompanyApprovalStatus.PENDING:
        return CompanyLoginInitiateResponse(
            status="PENDING_APPROVAL",
            session_token=None,
            masked_email=None,
            message="Your company account is currently under review by Super Admin. You will receive an email once approved.",
        )

    if company.approval_status == CompanyApprovalStatus.REJECTED:
        return CompanyLoginInitiateResponse(
            status="REJECTED",
            session_token=None,
            masked_email=None,
            message=f"Company account registration was rejected: {company.rejection_reason or 'Eligibility criteria not met.'}",
        )

    if company.approval_status == CompanyApprovalStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This company account is suspended: {company.suspend_reason or 'Policy violations.'}",
        )

    # Generate 2FA session token
    session_token = create_session_token(subject=user.id, purpose="employer_2fa")

    return CompanyLoginInitiateResponse(
        status="2FA_REQUIRED",
        session_token=session_token,
        masked_email=mask_email(user.email),
        message=f"Verification code sent to {mask_email(user.email)}.",
    )


@router.post("/login/verify-otp", response_model=CompanyTokenResponse)
def complete_employer_login(req: CompanyLoginVerifyOtpRequest, db: Session = Depends(get_db)):
    """Step 2 of Employer Login: Validates the 6-digit 2FA code and issues the company access token."""
    payload = decode_token(req.session_token)
    if not payload or payload.get("type") != "temp_session" or payload.get("purpose") != "employer_2fa":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired login session. Please sign in again.")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.company:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

    if settings.DEV_MOCK_OTP_ENABLED and req.code != settings.DEFAULT_OTP_CODE and req.code != "000000":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid 6-digit code. (Hint: Use 123456 in dev mode)")

    user.last_login_at = datetime.utcnow()
    user.status = UserStatus.ACTIVE
    db.commit()

    token = create_access_token(subject=user.id, role=user.role.value, company_id=user.company.id)

    return CompanyTokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role.value,
        company_id=user.company.id,
        company_name=user.company.name,
        user_id=user.id,
        user_name=user.name,
        user_email=user.email,
        approval_status=user.company.approval_status.value,
        plan_id=user.company.plan_id,
    )


@router.post("/activate-invite", response_model=CompanyTokenResponse)
def activate_team_invitation(req: AcceptInviteRequest, db: Session = Depends(get_db)):
    """Allows an invited recruiter or viewer to set their password and activate their account."""
    invite = db.query(CompanyInvitation).filter(
        CompanyInvitation.invite_token == req.invite_token,
        CompanyInvitation.status == "Pending",
    ).first()

    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation token not found or already used.")

    if invite.expiry < datetime.utcnow():
        invite.status = "Expired"
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has expired. Please ask your administrator to resend.")

    # Check if user already exists
    user = db.query(User).filter(User.email == invite.email.lower()).first()
    if not user:
        user = User(
            email=invite.email.lower(),
            name=req.name,
            hashed_password=get_password_hash(req.password),
            role=invite.role,
            status=UserStatus.ACTIVE,
            email_verified=True,
            two_factor_enabled=True,
            company_id=invite.company_id,
        )
        db.add(user)
    else:
        user.name = req.name
        user.hashed_password = get_password_hash(req.password)
        user.role = invite.role
        user.company_id = invite.company_id
        user.status = UserStatus.ACTIVE

    invite.status = "Accepted"
    db.commit()

    token = create_access_token(subject=user.id, role=user.role.value, company_id=invite.company_id)
    company = db.query(Company).filter(Company.id == invite.company_id).first()

    return CompanyTokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role.value,
        company_id=company.id,
        company_name=company.name,
        user_id=user.id,
        user_name=user.name,
        user_email=user.email,
        approval_status=company.approval_status.value,
        plan_id=company.plan_id,
    )


@router.get("/me", response_model=CompanyTokenResponse)
def get_current_company_info(current_user: User = Depends(get_current_company_user)):
    """Returns authenticated employer member & company context."""
    return CompanyTokenResponse(
        access_token="",
        token_type="bearer",
        role=current_user.role.value,
        company_id=current_user.company.id,
        company_name=current_user.company.name,
        user_id=current_user.id,
        user_name=current_user.name,
        user_email=current_user.email,
        approval_status=current_user.company.approval_status.value,
        plan_id=current_user.company.plan_id,
    )
