# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/audit_logs/schemas.py
# Purpose : Schemas for Admin Audit Logs
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class AuditLogItemSchema(BaseModel):
    id: int
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    user_type: Optional[str] = None
    action: str
    module: str
    description: Optional[str] = None
    ip_address: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
