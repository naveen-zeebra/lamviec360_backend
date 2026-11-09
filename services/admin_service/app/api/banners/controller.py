from typing import Dict, Any, Optional
from fastapi import Request
from sqlalchemy.orm import Session

from shared.models import AdminUser, Banner
from shared.utils import log_audit_event
from .schemas import (
    BannerCreate,
    BannerUpdate,
    BannerStatusUpdate,
)
from . import service


def list_banners_controller(
    db: Session,
    page: int = 1,
    page_size: int = 15,
    search: Optional[str] = None,
    placement: Optional[str] = None,
    category: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> Dict[str, Any]:
    return service.list_banners(
        db,
        page=page,
        page_size=page_size,
        search=search,
        placement=placement,
        category=category,
        status_filter=status_filter,
    )


def create_banner_controller(
    db: Session,
    payload: BannerCreate,
    admin_user: AdminUser,
    request: Request,
) -> Banner:
    banner = service.create_banner(db, payload, admin_user=admin_user)

    log_audit_event(
        db,
        action="CREATE_BANNER",
        module="COMMERCIAL",
        description=f"Admin {admin_user.email} created advertisement banner '{banner.title}' (ID #{banner.id}) for placement '{banner.placement}'",
        user_id=admin_user.id,
        user_email=admin_user.email,
        user_type="admin",
        request=request,
        details={
            "banner_id": banner.id,
            "title": banner.title,
            "placement": banner.placement,
            "category": banner.category,
            "is_active": banner.is_active,
        },
    )
    return banner


def update_banner_controller(
    db: Session,
    banner_id: int,
    payload: BannerUpdate,
    admin_user: AdminUser,
    request: Request,
) -> Banner:
    banner = service.update_banner(db, banner_id, payload)

    log_audit_event(
        db,
        action="UPDATE_BANNER",
        module="COMMERCIAL",
        description=f"Admin {admin_user.email} updated advertisement banner '{banner.title}' (ID #{banner.id})",
        user_id=admin_user.id,
        user_email=admin_user.email,
        user_type="admin",
        request=request,
        details={
            "banner_id": banner.id,
            "title": banner.title,
            "placement": banner.placement,
            "category": banner.category,
            "is_active": banner.is_active,
        },
    )
    return banner


def toggle_banner_status_controller(
    db: Session,
    banner_id: int,
    payload: BannerStatusUpdate,
    admin_user: AdminUser,
    request: Request,
) -> Banner:
    banner = service.toggle_banner_status(db, banner_id, payload)

    status_str = "ACTIVATED" if banner.is_active else "DEACTIVATED"
    log_audit_event(
        db,
        action="TOGGLE_BANNER_STATUS",
        module="COMMERCIAL",
        description=f"Admin {admin_user.email} {status_str} banner '{banner.title}' (ID #{banner.id})",
        user_id=admin_user.id,
        user_email=admin_user.email,
        user_type="admin",
        request=request,
        details={
            "banner_id": banner.id,
            "title": banner.title,
            "is_active": banner.is_active,
        },
    )
    return banner


def delete_banner_controller(
    db: Session,
    banner_id: int,
    admin_user: AdminUser,
    request: Request,
) -> None:
    banner = service.get_banner_by_id(db, banner_id)
    title = banner.title
    service.delete_banner(db, banner_id)

    log_audit_event(
        db,
        action="DELETE_BANNER",
        module="COMMERCIAL",
        description=f"Admin {admin_user.email} deleted advertisement banner '{title}' (ID #{banner_id})",
        user_id=admin_user.id,
        user_email=admin_user.email,
        user_type="admin",
        request=request,
        details={"banner_id": banner_id, "title": title},
    )
