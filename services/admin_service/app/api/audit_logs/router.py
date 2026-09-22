from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from shared.database.session import get_db
from shared.models import AuditLog, User
from shared.schemas import PaginatedResponse
from shared.utils import require_roles, paginated_response

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

    items = []
    for l in logs:
        items.append({
            "id": l.id,
            "user_id": l.user_id,
            "user_email": l.user_email or "System",
            "user_type": l.user_type,
            "action": l.action,
            "module": l.module,
            "description": l.description,
            "ip_address": l.ip_address,
            "details": l.details,
            "created_at": l.created_at,
        })

    return paginated_response(
        items=items,
        total_items=total_items,
        page=page,
        page_size=page_size,
        message="Audit logs retrieved",
    )
