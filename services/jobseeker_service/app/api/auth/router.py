# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/auth/router.py
# Purpose : Presentation layer (FastAPI endpoints) for Job Seeker Auth
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import User
from shared.schemas import APIResponse
from shared.utils import (
    get_current_jobseeker,
    get_current_active_user_optional,
    success_response,
    limiter,
)

from .schemas import (
    JobSeekerRegisterRequest,
    JobSeekerLoginRequest,
    RefreshTokenRequest,
    ChangePasswordRequest,
    SendVerificationEmailRequest,
    VerifyEmailRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from .controller import (
    register_jobseeker_controller,
    login_jobseeker_controller,
    get_me_controller,
    refresh_token_controller,
    change_password_controller,
    send_verification_email_controller,
    verify_email_controller,
    forgot_password_controller,
    reset_password_controller,
)

router = APIRouter(prefix="/auth", tags=["Job Seeker Auth"])


@router.post("/register", response_model=APIResponse[dict], summary="Register Job Seeker")
@limiter.limit("5/minute")
def register_jobseeker(req: JobSeekerRegisterRequest, request: Request, db: Session = Depends(get_db)):
    return success_response(
        data=register_jobseeker_controller(req, request, db),
        message="Registration successful",
    )


@router.post("/login", response_model=APIResponse[dict], summary="Job Seeker Login")
@limiter.limit("10/minute")
def login_jobseeker(req: JobSeekerLoginRequest, request: Request, db: Session = Depends(get_db)):
    return success_response(
        data=login_jobseeker_controller(req, request, db),
        message="Login successful",
    )


@router.get("/me", response_model=APIResponse[dict], summary="Get Current Job Seeker")
def get_me(user: User = Depends(get_current_jobseeker)):
    return success_response(data=get_me_controller(user), message="User profile fetched")


@router.post("/refresh", response_model=APIResponse[dict], summary="Refresh Access Token")
def refresh_token(req: RefreshTokenRequest, db: Session = Depends(get_db)):
    return success_response(data=refresh_token_controller(req, db))


@router.post("/change-password", response_model=APIResponse[None], summary="Change Password")
def change_password(
    req: ChangePasswordRequest,
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    change_password_controller(req, user, db)
    return success_response(message="Password updated successfully")


@router.post("/send-verification-email", response_model=APIResponse[dict], summary="Send Verification Email")
def send_verification_code(
    req: Optional[SendVerificationEmailRequest] = None,
    current_user: Optional[User] = Depends(get_current_active_user_optional),
    db: Session = Depends(get_db),
):
    return success_response(
        data=send_verification_email_controller(req, current_user, db),
        message="Verification code sent to your email",
    )


@router.post("/verify-email", response_model=APIResponse[dict], summary="Verify Email Code")
def verify_email(
    req: VerifyEmailRequest,
    request: Request,
    current_user: Optional[User] = Depends(get_current_active_user_optional),
    db: Session = Depends(get_db),
):
    return success_response(
        data=verify_email_controller(req, request, current_user, db),
        message="Email verified successfully",
    )


@router.post("/forgot-password", response_model=APIResponse[dict], summary="Forgot Password")
@limiter.limit("3/minute")
def forgot_password(req: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    data = forgot_password_controller(req, request, db)
    return success_response(
        data=data,
        message="If this email is registered, a password reset link has been sent.",
    )


@router.post("/reset-password", response_model=APIResponse[dict], summary="Reset Password")
def reset_password(req: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    reset_password_controller(req, request, db)
    return success_response(
        message="Password updated successfully. You can now login with your new password.",
    )
