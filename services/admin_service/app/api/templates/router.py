# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/templates/router.py
# Purpose : FastAPI router for Super Admin Global Template Management (sa07)
# ─────────────────────────────────────────────────────────────────────────────

from typing import List
from fastapi import APIRouter, Depends

from shared.models import User
from shared.schemas import APIResponse
from shared.utils import require_roles, success_response

from services.admin_service.app.api.templates.schemas import (
    MasterTemplateItem,
    MasterConfigResponse,
    UpdateMasterTemplateRequest,
    UpdateMasterConfigRequest,
)
from services.admin_service.app.api.templates.controller import (
    list_templates_controller,
    update_template_controller,
    get_config_controller,
    update_config_controller,
)

router = APIRouter(prefix="/notifications", tags=["Global Notification Templates"])


@router.get("/templates", response_model=APIResponse[List[MasterTemplateItem]], summary="List Global Master Templates (sa07)")
def list_global_templates(
    admin: User = Depends(require_roles(["super_admin", "admin"])),
):
    data = list_templates_controller()
    return success_response(data=data)


@router.put("/templates/{scenario_id}", response_model=APIResponse[MasterTemplateItem], summary="Update Master Template (sa07)")
def update_global_template(
    scenario_id: str,
    payload: UpdateMasterTemplateRequest,
    admin: User = Depends(require_roles(["super_admin", "admin"])),
):
    data = update_template_controller(scenario_id=scenario_id, payload=payload)
    return success_response(data=data, message="Master template updated successfully")


@router.get("/config", response_model=APIResponse[MasterConfigResponse], summary="Get Platform Notification Config")
def get_notification_config(
    admin: User = Depends(require_roles(["super_admin", "admin"])),
):
    data = get_config_controller()
    return success_response(data=data)


@router.put("/config", response_model=APIResponse[MasterConfigResponse], summary="Update Platform Notification Config")
def update_notification_config(
    payload: UpdateMasterConfigRequest,
    admin: User = Depends(require_roles(["super_admin", "admin"])),
):
    data = update_config_controller(payload=payload)
    return success_response(data=data, message="Platform notification configuration updated successfully")
