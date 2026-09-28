# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/auth/router.py
# Purpose : Presentation layer (FastAPI endpoints) for Admin Portal Auth
# ─────────────────────────────────────────────────────────────────────────────

from typing import Any
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.schemas import APIResponse
from shared.utils.jwt import get_current_user
from shared.utils.rate_limiter import limiter
from shared.utils.response import success_response

from .schemas import (
    AdminLoginRequest,
    RefreshTokenRequest,
    LogoutRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from .controller import (
    admin_login_controller,
    refresh_token_controller,
    logout_controller,
    logout_all_controller,
    forgot_password_controller,
    reset_password_controller,
    change_password_controller,
)

router = APIRouter(prefix="/auth", tags=["Admin Auth"])
admin_auth_router = router  # Alias for module naming flexibility


@router.post(
    "/login",
    response_model=APIResponse[dict],
    summary="Admin Login",
    description="Authenticate an administrator using email and password. Returns access and refresh tokens.",
)
@limiter.limit("5/minute")
def admin_login(request: Request, body: AdminLoginRequest, db: Session = Depends(get_db)):
    return success_response(
        data=admin_login_controller(body, request, db),
        message="Login successful",
    )


@router.post(
    "/refresh",
    response_model=APIResponse[dict],
    summary="Refresh Access Token",
    description="Exchange a valid refresh token for a new access token and a rotated refresh token.",
)
def refresh_token(body: RefreshTokenRequest, db: Session = Depends(get_db)):
    return success_response(
        data=refresh_token_controller(body, db),
        message="Token refreshed successfully",
    )


@router.post(
    "/refresh-token",
    response_model=APIResponse[dict],
    summary="Refresh Access Token (Legacy Alias)",
    description="Alias endpoint for frontend backward compatibility.",
    include_in_schema=False,
)
def refresh_token_alias(body: RefreshTokenRequest, db: Session = Depends(get_db)):
    return success_response(
        data=refresh_token_controller(body, db),
        message="Token refreshed successfully",
    )


@router.post(
    "/logout",
    response_model=APIResponse[dict],
    summary="Logout",
    description="Revoke the current refresh token.",
)
def logout(body: LogoutRequest, db: Session = Depends(get_db)):
    return success_response(
        data=logout_controller(body, db),
        message="Logged out successfully",
    )


@router.post(
    "/logout-all",
    response_model=APIResponse[dict],
    summary="Logout from All Devices",
    description="Revoke all active refresh tokens across all sessions/devices for the authenticated admin.",
)
def logout_all(current_user: Any = Depends(get_current_user), db: Session = Depends(get_db)):
    return success_response(
        data=logout_all_controller(current_user.id, db),
        message="Logged out from all devices",
    )


@router.post(
    "/forgot-password",
    response_model=APIResponse[dict],
    summary="Forgot Password",
    description="Generate a secure password reset token and dispatch an email with the reset link.",
)
@limiter.limit("3/minute")
def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    return success_response(
        data=forgot_password_controller(body, background_tasks, db),
        message="If the account exists, a password reset link has been dispatched.",
    )


@router.post(
    "/reset-password",
    response_model=APIResponse[dict],
    summary="Reset Password",
    description="Reset administrator password using a valid reset token.",
)
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    return success_response(
        data=reset_password_controller(body, db),
        message="Password reset successfully",
    )


@router.post(
    "/change-password",
    response_model=APIResponse[dict],
    summary="Change Password",
    description="Change administrator password after verifying the old password.",
)
def change_password(
    body: ChangePasswordRequest,
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return success_response(
        data=change_password_controller(body, current_user, db),
        message="Password changed successfully",
    )
