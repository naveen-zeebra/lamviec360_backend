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
    OAuthLoginRequest,
    GoogleLoginRequest,
    ZaloLoginRequest,
    LinkedInLoginRequest,
    FacebookLoginRequest,
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
    oauth_login_controller,
    get_oauth_url_controller,
    get_oauth_providers_controller,
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


# ─────────────────────────────────────────────────────────────────────────────
# OAuth Endpoints (Google, Zalo, LinkedIn, Facebook)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/oauth/providers", response_model=APIResponse[list], summary="Get Available OAuth Providers")
def get_oauth_providers():
    return success_response(
        data=get_oauth_providers_controller(),
        message="Available OAuth providers retrieved",
    )


@router.get("/oauth/{provider}/url", response_model=APIResponse[dict], summary="Get OAuth Authorization URL")
def get_oauth_url(provider: str, redirect_uri: Optional[str] = None, state: Optional[str] = None):
    return success_response(
        data=get_oauth_url_controller(provider, redirect_uri, state),
        message=f"{provider.capitalize()} authorization URL generated",
    )


@router.post("/oauth/login", response_model=APIResponse[dict], summary="Unified OAuth Login/Register")
@limiter.limit("20/minute")
def oauth_login(req: OAuthLoginRequest, request: Request, db: Session = Depends(get_db)):
    return success_response(
        data=oauth_login_controller(req, request, db),
        message=f"Logged in successfully via {req.provider.capitalize()}",
    )


@router.post("/google", response_model=APIResponse[dict], summary="Google OAuth Login")
@limiter.limit("20/minute")
def google_login(req: GoogleLoginRequest, request: Request, db: Session = Depends(get_db)):
    oauth_req = OAuthLoginRequest(
        provider="google",
        token=req.token,
        code=req.code,
        redirect_uri=req.redirect_uri,
        email=req.email,
        name=req.name,
        avatar_url=req.avatar_url,
        provider_user_id=req.google_id,
    )
    return success_response(
        data=oauth_login_controller(oauth_req, request, db),
        message="Logged in successfully via Google",
    )


@router.post("/zalo", response_model=APIResponse[dict], summary="Zalo OAuth Login")
@limiter.limit("20/minute")
def zalo_login(req: ZaloLoginRequest, request: Request, db: Session = Depends(get_db)):
    oauth_req = OAuthLoginRequest(
        provider="zalo",
        token=req.token,
        code=req.code,
        redirect_uri=req.redirect_uri,
        code_verifier=req.code_verifier,
        email=req.email,
        name=req.name,
        avatar_url=req.avatar_url,
        provider_user_id=req.zalo_id,
    )
    return success_response(
        data=oauth_login_controller(oauth_req, request, db),
        message="Logged in successfully via Zalo",
    )


@router.post("/linkedin", response_model=APIResponse[dict], summary="LinkedIn OAuth Login")
@limiter.limit("20/minute")
def linkedin_login(req: LinkedInLoginRequest, request: Request, db: Session = Depends(get_db)):
    oauth_req = OAuthLoginRequest(
        provider="linkedin",
        token=req.token,
        code=req.code,
        redirect_uri=req.redirect_uri,
        email=req.email,
        name=req.name,
        avatar_url=req.avatar_url,
        provider_user_id=req.linkedin_id,
    )
    return success_response(
        data=oauth_login_controller(oauth_req, request, db),
        message="Logged in successfully via LinkedIn",
    )


@router.post("/facebook", response_model=APIResponse[dict], summary="Facebook OAuth Login")
@limiter.limit("20/minute")
def facebook_login(req: FacebookLoginRequest, request: Request, db: Session = Depends(get_db)):
    oauth_req = OAuthLoginRequest(
        provider="facebook",
        token=req.token,
        code=req.code,
        redirect_uri=req.redirect_uri,
        email=req.email,
        name=req.name,
        avatar_url=req.avatar_url,
        provider_user_id=req.facebook_id,
    )
    return success_response(
        data=oauth_login_controller(oauth_req, request, db),
        message="Logged in successfully via Facebook",
    )
