# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/templates/controller.py
# Purpose : Controller layer for Super Admin Global Template Management (sa07)
# ─────────────────────────────────────────────────────────────────────────────

from typing import List, Optional
from fastapi import Request
from sqlalchemy.orm import Session
from shared.models import User
from shared.utils import log_audit_event
from services.admin_service.app.api.templates.schemas import (
    MasterTemplateItem,
    MasterConfigResponse,
    UpdateMasterTemplateRequest,
    UpdateMasterConfigRequest,
)
from services.admin_service.app.api.templates import service


def list_templates_controller() -> List[MasterTemplateItem]:
    return service.list_master_templates()


def update_template_controller(
    scenario_id: str,
    payload: UpdateMasterTemplateRequest,
    current_admin: Optional[User] = None,
    db: Optional[Session] = None,
    request: Optional[Request] = None,
) -> MasterTemplateItem:
    updated = service.update_master_template(scenario_id=scenario_id, payload=payload)
    if db and current_admin:
        log_audit_event(
            db,
            action="UPDATE_EMAIL_TEMPLATE",
            module="TEMPLATES",
            description=f"Admin {current_admin.email} updated master template '{scenario_id}'",
            user_id=current_admin.id,
            user_email=current_admin.email,
            user_type=current_admin.user_type,
            request=request,
            details={"scenario_id": scenario_id, "subject": payload.subject_template},
        )
    return updated


def get_config_controller() -> MasterConfigResponse:
    return service.get_platform_notification_config()


def update_config_controller(
    payload: UpdateMasterConfigRequest,
    current_admin: Optional[User] = None,
    db: Optional[Session] = None,
    request: Optional[Request] = None,
) -> MasterConfigResponse:
    updated = service.update_platform_notification_config(payload=payload)
    if db and current_admin:
        log_audit_event(
            db,
            action="UPDATE_NOTIFICATION_CONFIG",
            module="CONFIGURATION",
            description=f"Admin {current_admin.email} modified platform notification dispatch config",
            user_id=current_admin.id,
            user_email=current_admin.email,
            user_type=current_admin.user_type,
            request=request,
        )
    return updated
