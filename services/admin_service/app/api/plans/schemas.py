# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/plans/schemas.py
# Purpose : Schemas for Admin Subscription Plan Management
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List
from pydantic import BaseModel, Field


class PlanItemSchema(BaseModel):
    id: str
    price: float
    limits: Optional[int] = None
    features: List[str] = Field(default_factory=list)


class PlanUpdateRequest(BaseModel):
    price: Optional[float] = None
    limits: Optional[int] = None
    features: Optional[List[str]] = None
