# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/plans/schemas.py
# Purpose : Schemas for Admin Subscription Plan Management
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Union, Any
from pydantic import BaseModel, Field


class PlanItemSchema(BaseModel):
    id: str
    name: Optional[str] = None
    tier: Optional[str] = None
    price: Union[str, float]
    posting_limit: Optional[int] = None
    limits: Optional[int] = None
    retention_months: Optional[int] = 12
    ai_features: Optional[bool] = False
    blurb: Optional[str] = None
    features: List[str] = Field(default_factory=list)
    active: Optional[bool] = True


class PlanUpdateRequest(BaseModel):
    name: Optional[str] = None
    price: Optional[Union[str, float]] = None
    limits: Optional[int] = None
    posting_limit: Optional[int] = None
    retention_months: Optional[int] = None
    ai_features: Optional[bool] = None
    blurb: Optional[str] = None
    features: Optional[List[str]] = None
    active: Optional[bool] = None
