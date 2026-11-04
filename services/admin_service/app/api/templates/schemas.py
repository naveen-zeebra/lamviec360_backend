# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/templates/schemas.py
# Purpose : Schemas for Super Admin Global Template Management (sa07 / FSD-006)
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class MasterTemplateItem(BaseModel):
    scenario_id: str
    category: str
    badge_vi: str
    badge_en: str
    subject_vi: str
    subject_en: str
    headline_vi: str
    headline_en: str
    body_vi: str
    body_en: str
    cta_text_vi: Optional[str] = None
    cta_text_en: Optional[str] = None
    cta_url: Optional[str] = None
    is_active: bool = True


class MasterConfigResponse(BaseModel):
    default_language: str = "vi"
    supported_languages: List[str] = ["vi", "en"]
    global_suppression_enabled: bool = True
    max_rejection_delay_days: int = 7


class UpdateMasterTemplateRequest(BaseModel):
    subject_vi: Optional[str] = None
    subject_en: Optional[str] = None
    headline_vi: Optional[str] = None
    headline_en: Optional[str] = None
    body_vi: Optional[str] = None
    body_en: Optional[str] = None
    is_active: Optional[bool] = None


class UpdateMasterConfigRequest(BaseModel):
    default_language: Optional[str] = Field(None, description="Must be 'vi' (standard) or 'en'")
    max_rejection_delay_days: Optional[int] = Field(None, ge=1, le=30)

