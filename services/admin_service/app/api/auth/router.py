from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from datetime import datetime
from shared.database.session import get_db
from shared.models import User, AdminUser
from shared.schemas import (
    LoginRequest,
    RefreshTokenRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
    APIResponse,
)
from shared.utils import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    success_response,
    log_audit_event,
)

router = APIRouter(prefix="/auth", tags=["Admin Auth"])

@router.post("/login", response_model=APIResponse[dict])
def admin_login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    # 1. Check dedicated AdminUser table first
    admin = db.query(AdminUser).filter(AdminUser.email == req.email.lower(), AdminUser.is_deleted == False).first()
    if admin and verify_password(req.password, admin.password_hash):
        if not admin.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin account is inactive")

        role_code = admin.role_rel.code if admin.role_rel else "super_admin"
        permissions = []
        if admin.role_rel:
            for p in admin.role_rel.permissions:
                actions = []
                if p.can_view: actions.append("view")
                if p.can_create: actions.append("create")
                if p.can_edit: actions.append("edit")
                if p.can_delete: actions.append("delete")
                permissions.append(f"{p.module_key.lower()}:{','.join(actions)}")

        access_token = create_access_token(
            user_id=admin.id,
            email=admin.email,
            user_type="super_admin" if "super" in role_code else "admin",
            roles=[role_code],
            permissions=permissions,
        )
        refresh_token = create_refresh_token(admin.id)
        admin.last_login = datetime.utcnow()
        db.commit()

        log_audit_event(
            db,
            action="ADMIN_LOGIN",
            module="ADMIN_AUTH",
            description=f"Platform administrator logged in: {admin.email} ({admin.role_name})",
            user_id=admin.id,
            user_email=admin.email,
            user_type="super_admin",
            request=request,
        )

        return success_response(
            data={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {
                    "id": str(admin.id),
                    "email": admin.email,
                    "first_name": admin.first_name,
                    "last_name": admin.last_name,
                    "name": admin.full_name,
                    "full_name": admin.full_name,
                    "role": admin.role_name,
                    "roles": [role_code],
                    "permissions": admin.permissions_dict,
                    "avatar": admin.avatar_url,
                },
            },
            message="Login successful",
        )

    # 2. Fallback check for legacy admin users in User table
    user = db.query(User).filter(User.email == req.email.lower()).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
        )

    # Validate admin privileges
    is_admin = user.is_superuser or user.user_type in ["super_admin", "admin"]
    if not is_admin:
        role_codes = [r.code for r in user.roles]
        if not any(code in ["super_admin", "admin"] for code in role_codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access restricted to administrative staff only",
            )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is inactive",
        )

    roles = [r.code for r in user.roles]
    permissions = []
    for r in user.roles:
        for p in r.permissions:
            permissions.append(f"{p.module}:{p.action}")

    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        user_type=user.user_type,
        roles=roles,
        permissions=list(set(permissions)),
    )
    refresh_token = create_refresh_token(user.id)

    log_audit_event(
        db,
        action="ADMIN_LOGIN",
        module="ADMIN_AUTH",
        description=f"Admin logged in: {user.email}",
        user_id=user.id,
        user_email=user.email,
        user_type=user.user_type,
        request=request,
    )

    return success_response(
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.full_name,
                "full_name": user.full_name,
                "role": roles[0] if roles else "admin",
                "roles": roles,
                "permissions": list(set(permissions)),
                "avatar": user.avatar_url,
                "avatar_url": user.avatar_url,
            },
        },
        message="Login successful",
    )


@router.post("/refresh-token", response_model=APIResponse[dict])
def refresh_token(req: RefreshTokenRequest, db: Session = Depends(get_db)):
    payload = decode_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token type")
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not active")
    
    roles = [r.code for r in user.roles]
    new_access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        user_type=user.user_type,
        roles=roles,
    )
    return success_response(data={"access_token": new_access_token, "token_type": "bearer"})


@router.post("/forgot-password", response_model=APIResponse[None])
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.lower()).first()
    # Return success regardless of whether email exists to prevent user enumeration
    return success_response(message="If the account exists, a password reset link has been dispatched.")


@router.post("/reset-password", response_model=APIResponse[None])
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    # Mock token validation for dev/demo purposes
    if not req.token:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    return success_response(message="Password reset successfully. You may now log in.")


@router.post("/change-password", response_model=APIResponse[None])
def change_password(
    req: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(req.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    user.hashed_password = hash_password(req.new_password)
    db.commit()
    return success_response(message="Admin password updated successfully")
