# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/audit_logs/service.py
# Purpose : Domain & query logic for System Audit Logs
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from shared.models import AuditLog
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("admin_audit_logs_service")


def serialize_audit_log(l: AuditLog) -> Dict[str, Any]:
    """Serialize AuditLog ORM model to dictionary."""
    return {
        "id": l.id,
        "user_id": l.user_id,
        "user_email": l.user_email or "System",
        "user_type": l.user_type,
        "action": l.action,
        "module": l.module,
        "description": l.description,
        "ip_address": l.ip_address,
        "details": l.details,
        "created_at": l.created_at.isoformat() if l.created_at else None,
    }


@service_error_handler
def query_audit_logs(
    db: Session,
    module: Optional[str] = None,
    action: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 15,
) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieve filtered and paginated audit logs."""
    query = db.query(AuditLog)

    if module:
        query = query.filter(AuditLog.module == module)
    if action:
        query = query.filter(AuditLog.action == action)
    if search:
        query = query.filter(AuditLog.description.ilike(f"%{search.strip()}%"))

    total_items = query.count()
    offset = (page - 1) * page_size
    logs = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(page_size).all()

    items = [serialize_audit_log(l) for l in logs]
    return items, total_items
