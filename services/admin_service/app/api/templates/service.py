# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/templates/service.py
# Purpose : Business logic for Super Admin Global Template Management (sa07)
# ─────────────────────────────────────────────────────────────────────────────

from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from shared.notifications.templates.catalog import NOTIFICATION_CATALOG
from services.admin_service.app.api.templates.schemas import (
    MasterTemplateItem,
    MasterConfigResponse,
    UpdateMasterTemplateRequest,
    UpdateMasterConfigRequest,
)

# In-memory overrides store for customized system templates
_CUSTOM_OVERRIDES: Dict[str, Dict[str, Any]] = {}
_PLATFORM_CONFIG = {
    "default_language": "vi",
    "supported_languages": ["vi", "en"],
    "global_suppression_enabled": True,
    "max_rejection_delay_days": 7,
}


def list_master_templates() -> List[MasterTemplateItem]:
    """Retrieve all 19 system templates with dual language content."""
    items: List[MasterTemplateItem] = []
    for scn_id, data in NOTIFICATION_CATALOG.items():
        override = _CUSTOM_OVERRIDES.get(scn_id, {})
        vi_pack = override.get("vi", data.get("vi", {}))
        en_pack = override.get("en", data.get("en", {}))

        items.append(
            MasterTemplateItem(
                scenario_id=scn_id,
                category=data.get("category", "General"),
                badge_vi=data.get("badge_vi", ""),
                badge_en=data.get("badge_en", ""),
                subject_vi=vi_pack.get("subject", ""),
                subject_en=en_pack.get("subject", ""),
                headline_vi=vi_pack.get("headline", ""),
                headline_en=en_pack.get("headline", ""),
                body_vi=vi_pack.get("body", ""),
                body_en=en_pack.get("body", ""),
                cta_text_vi=vi_pack.get("cta_text"),
                cta_text_en=en_pack.get("cta_text"),
                cta_url=vi_pack.get("cta_url"),
                is_active=override.get("is_active", True),
            )
        )
    return items


def update_master_template(
    scenario_id: str, payload: UpdateMasterTemplateRequest
) -> MasterTemplateItem:
    """Update master template content or active status."""
    if scenario_id not in NOTIFICATION_CATALOG:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found.")

    base = NOTIFICATION_CATALOG[scenario_id]
    override = _CUSTOM_OVERRIDES.setdefault(
        scenario_id,
        {
            "vi": dict(base.get("vi", {})),
            "en": dict(base.get("en", {})),
            "is_active": True,
        },
    )

    if payload.subject_vi is not None:
        override["vi"]["subject"] = payload.subject_vi
    if payload.subject_en is not None:
        override["en"]["subject"] = payload.subject_en
    if payload.headline_vi is not None:
        override["vi"]["headline"] = payload.headline_vi
    if payload.headline_en is not None:
        override["en"]["headline"] = payload.headline_en
    if payload.body_vi is not None:
        override["vi"]["body"] = payload.body_vi
    if payload.body_en is not None:
        override["en"]["body"] = payload.body_en
    if payload.is_active is not None:
        override["is_active"] = payload.is_active

    return MasterTemplateItem(
        scenario_id=scenario_id,
        category=base.get("category", "General"),
        badge_vi=base.get("badge_vi", ""),
        badge_en=base.get("badge_en", ""),
        subject_vi=override["vi"].get("subject", ""),
        subject_en=override["en"].get("subject", ""),
        headline_vi=override["vi"].get("headline", ""),
        headline_en=override["en"].get("headline", ""),
        body_vi=override["vi"].get("body", ""),
        body_en=override["en"].get("body", ""),
        cta_text_vi=override["vi"].get("cta_text"),
        cta_text_en=override["en"].get("cta_text"),
        cta_url=override["vi"].get("cta_url"),
        is_active=override.get("is_active", True),
    )


def get_platform_notification_config() -> MasterConfigResponse:
    """Retrieve global notification rules and language settings."""
    return MasterConfigResponse(**_PLATFORM_CONFIG)


def update_platform_notification_config(
    payload: UpdateMasterConfigRequest,
) -> MasterConfigResponse:
    """Update global notification settings and default language."""
    if payload.default_language is not None:
        if payload.default_language.lower() in ("vi", "en"):
            _PLATFORM_CONFIG["default_language"] = payload.default_language.lower()
    if payload.max_rejection_delay_days is not None:
        _PLATFORM_CONFIG["max_rejection_delay_days"] = payload.max_rejection_delay_days

    return MasterConfigResponse(**_PLATFORM_CONFIG)

