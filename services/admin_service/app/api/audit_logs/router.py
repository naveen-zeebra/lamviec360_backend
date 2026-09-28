# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/audit_logs/router.py
# Purpose : HTTP Routing endpoints for Admin Audit Logs
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import User
from shared.schemas import PaginatedResponse
from shared.utils import require_roles, paginated_response
from .controller import list_audit_logs_controller

router = APIRouter(prefix="/audit-logs", tags=["Admin Audit Logs"])


@router.get("", response_model=PaginatedResponse[dict])
def list_audit_logs(
    module: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=100),
    current_admin: User = Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
):
    """Retrieve audit logs with optional filtering by module, action, or description text."""
    items, total_items = list_audit_logs_controller(
        db=db,
        module=module,
        action=action,
        search=search,
        page=page,
        page_size=page_size,
    )
    return paginated_response(
        items=items,
        total_items=total_items,
        page=page,
        page_size=page_size,
        message="Audit logs retrieved",
    )
