import json
from typing import Optional, Any
from fastapi import Request
from sqlalchemy.orm import Session
from shared.models.audit_log import AuditLog
from shared.utils.logger import get_logger

logger = get_logger("audit")

def log_audit_event(
    db: Session,
    action: str,
    module: str,
    description: Optional[str] = None,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    user_type: Optional[str] = None,
    request: Optional[Request] = None,
    details: Optional[Any] = None,
) -> AuditLog:
    ip_address = None
    user_agent = None
    
    if request:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

    details_str = json.dumps(details) if isinstance(details, (dict, list)) else str(details) if details else None

    entry = AuditLog(
        user_id=user_id,
        user_email=user_email,
        user_type=user_type,
        action=action,
        module=module,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details_str,
    )
    db.add(entry)
    try:
        db.commit()
        db.refresh(entry)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to record audit log: {str(e)}")
    
    return entry
