# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/templates/controller.py
# Purpose : Controller layer for Super Admin Global Template Management (sa07)
# ─────────────────────────────────────────────────────────────────────────────

from typing import List
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
    scenario_id: str, payload: UpdateMasterTemplateRequest
) -> MasterTemplateItem:
    return service.update_master_template(scenario_id=scenario_id, payload=payload)


def get_config_controller() -> MasterConfigResponse:
    return service.get_platform_notification_config()


def update_config_controller(payload: UpdateMasterConfigRequest) -> MasterConfigResponse:
    return service.update_platform_notification_config(payload=payload)

