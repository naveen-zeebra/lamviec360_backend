from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class TenantActionRequest(BaseModel):
    reason: Optional[str] = None


class TenantPlanUpdateRequest(BaseModel):
    plan_id: str


class UserStatusUpdateRequest(BaseModel):
    status: str  # "Active", "Suspended"


class ModerationActionRequest(BaseModel):
    action: str  # "Dismissed" or "Actioned"
    resolution_notes: Optional[str] = None


class SubscriptionPlanUpdateRequest(BaseModel):
    name: Optional[str] = None
    price: Optional[str] = None
    posting_limit: Optional[int] = None
    retention_months: Optional[int] = None
    ai_features: Optional[bool] = None
    blurb: Optional[str] = None
    features: Optional[List[str]] = None
    active: Optional[bool] = None


class AnalyticsOverview(BaseModel):
    total_users: int
    total_tenants: int
    pending_tenants: int
    active_jobs: int
    total_applications: int
    user_growth: List[Dict[str, Any]] = []
    tenant_growth: List[Dict[str, Any]] = []
