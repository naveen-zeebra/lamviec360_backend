# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/audit_logs/controller.py
# Purpose : Orchestration layer for Admin Audit Logs
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from shared.utils.logger import get_logger
from .service import query_audit_logs

logger = get_logger("admin_audit_logs_controller")


def list_audit_logs_controller(
    db: Session,
    module: Optional[str] = None,
    action: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 15,
) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieve filtered and paginated audit logs."""
    return query_audit_logs(
        db=db,
        module=module,
        action=action,
        search=search,
        page=page,
        page_size=page_size,
    )
