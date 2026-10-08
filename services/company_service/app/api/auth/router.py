# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/auth/router.py
# Purpose : Presentation layer (FastAPI endpoints) for Company Portal Auth
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, Any
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import User
from shared.schemas import APIResponse
from shared.utils import (
    get_current_company_user,
    get_current_user,
    get_current_active_user_optional,
    success_response,
    limiter,
)

from .schemas import (
    CompanyRegisterRequest,
    CompanyLoginRequest,
    LoginInitiateRequest,
    VerifyOtpRequest,
    SendVerificationEmailRequest,
    VerifyEmailRequest,
    ActivateInviteRequest,
    RefreshTokenRequest,
    ChangePasswordRequest,
)
from shared.schemas.company_team import InvitationAcceptRequest
from .controller import (
    register_company_controller,
    login_company_controller,
    initiate_otp_login_controller,
    verify_otp_login_controller,
    send_verification_email_controller,
    verify_email_controller,
    get_invite_controller,
    activate_invite_controller,
    get_company_me_controller,
    refresh_token_controller,
    change_password_controller,
)

router = APIRouter(prefix="/auth", tags=["Company Auth"])


@router.post("/register", response_model=APIResponse[dict], summary="Register Company")
@limiter.limit("5/minute")
def register_company(req: CompanyRegisterRequest, request: Request, db: Session = Depends(get_db)):
    return success_response(
        data=register_company_controller(req, request, db),
        message="Company account created successfully",
    )


@router.post("/login", response_model=APIResponse[dict], summary="Company Login")
@limiter.limit("10/minute")
def login_company(req: CompanyLoginRequest, request: Request, db: Session = Depends(get_db)):
    return success_response(
        data=login_company_controller(req, request, db),
        message="Login successful",
    )


@router.post("/login/initiate", response_model=APIResponse[dict], summary="Initiate 2FA/OTP Login")
def initiate_otp_login(req: LoginInitiateRequest, db: Session = Depends(get_db)):
    data = initiate_otp_login_controller(req, db)
    return success_response(data=data, message=data.get("message", "OTP sent to email/phone"))


@router.post("/login/verify-otp", response_model=APIResponse[dict], summary="Verify OTP Login")
def verify_otp_login(req: VerifyOtpRequest, request: Request, db: Session = Depends(get_db)):
    return success_response(
        data=verify_otp_login_controller(req, request, db),
        message="OTP verified successfully",
    )


@router.post("/send-verification-email", response_model=APIResponse[dict], summary="Send Verification Email")
@router.post("/resend-verification-email", response_model=APIResponse[dict], summary="Resend Verification Email")
def send_company_verification_email(
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


@router.get("/invite/{token}", response_model=APIResponse[dict], summary="Get Invitation Details")
def get_invite_by_token(token: str, db: Session = Depends(get_db)):
    return success_response(data=get_invite_controller(db, token))


@router.post("/activate-invite", response_model=APIResponse[dict], summary="Activate Team Invitation")
def activate_team_invite(req: ActivateInviteRequest, db: Session = Depends(get_db)):
    return success_response(
        data=activate_invite_controller(req, db),
        message="Team member account activated",
    )


@router.get("/invitation/verify", response_model=APIResponse[dict], summary="Verify Team Invitation Token")
def verify_team_invitation_endpoint(token: str, db: Session = Depends(get_db)):
    from .controller import verify_team_invitation_controller
    return success_response(
        data=verify_team_invitation_controller(token, db),
        message="Invitation is valid",
    )


@router.post("/invitation/accept", response_model=APIResponse[dict], summary="Accept Team Invitation and Set Password")
def accept_team_invitation_endpoint(req: InvitationAcceptRequest, db: Session = Depends(get_db)):
    from .controller import accept_team_invitation_controller
    return success_response(
        data=accept_team_invitation_controller(req, db),
        message="Account activated successfully",
    )


@router.get("/me", response_model=APIResponse[dict], summary="Get Current Company User")
def get_company_me(user: Any = Depends(get_current_company_user), db: Session = Depends(get_db)):
    return success_response(data=get_company_me_controller(user, db))


@router.post("/refresh", response_model=APIResponse[dict], summary="Refresh Access Token")
def refresh_token(req: RefreshTokenRequest, db: Session = Depends(get_db)):
    return success_response(data=refresh_token_controller(req, db))


@router.post("/change-password", response_model=APIResponse[None], summary="Change Password")
def change_password(
    req: ChangePasswordRequest,
    user: Any = Depends(get_current_company_user),
    db: Session = Depends(get_db),
):
    res = change_password_controller(req, user, db)
    return success_response(message=res.get("message", "Password updated successfully"))


@router.get("/validate-tax-id/{tax_id}", response_model=APIResponse[dict], summary="Validate Vietnam Business Tax ID via VietQR")
def validate_tax_id(tax_id: str, db: Session = Depends(get_db)):
    """
    Validates a Vietnamese Tax ID / Business code using the official VietQR National Registry API.
    API: https://api.vietqr.io/v2/business/{tax_id}
    """
    import re
    from shared.models import CompanyProfile
    from shared.utils.logger import get_logger

    logger = get_logger("company_auth")
    clean_id = re.sub(r"[^0-9\-]", "", tax_id.strip())
    if not clean_id or len(clean_id) < 8:
        return success_response(
            data={"valid": False, "tax_id": clean_id, "error": "Tax ID must be at least 8 digits"},
            message="Invalid Tax ID format",
        )

    url = f"https://api.vietqr.io/v2/business/{clean_id}"
    try:
        import httpx
        with httpx.Client(timeout=6.0) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                body = resp.json()
                if body.get("code") == "00" and body.get("data"):
                    b_data = body["data"]
                    existing = (
                        db.query(CompanyProfile)
                        .filter(CompanyProfile.tax_code == clean_id)
                        .first()
                    )
                    return success_response(
                        data={
                            "valid": True,
                            "tax_id": clean_id,
                            "business": b_data,
                            "already_registered": existing is not None,
                        },
                        message="Valid Business Tax ID",
                    )
                else:
                    return success_response(
                        data={
                            "valid": False,
                            "tax_id": clean_id,
                            "error": body.get("desc") or "Tax ID not found in Vietnam Business Registry",
                            "business": None,
                        },
                        message="Tax ID not found",
                    )
    except Exception as e:
        logger.warning(f"VietQR lookup failed for {clean_id}: {e}")
        is_format_ok = bool(re.match(r"^\d{10}(\-\d{3}|\d{3})?$", clean_id))
        return success_response(
            data={
                "valid": is_format_ok,
                "tax_id": clean_id,
                "business": None,
                "fallback": True,
                "error": None if is_format_ok else "Tax ID format invalid (expected 10 or 13 digits)",
            },
            message="Tax ID validated with fallback",
        )

