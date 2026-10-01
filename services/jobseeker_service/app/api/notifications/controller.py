# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/notifications/controller.py
# Purpose : Orchestration layer for Job Seeker Notifications
# ─────────────────────────────────────────────────────────────────────────────

from typing import List, Dict, Any
from fastapi import HTTPException
from sqlalchemy.orm import Session

from shared.models import User
from . import service
from .schemas import CreateNotificationRequest


def _serialize_notification(notif) -> Dict[str, Any]:
    created_at_dt = notif.created_at
    date_str = created_at_dt.strftime("%Y-%m-%d") if created_at_dt else ""
    iso_str = created_at_dt.isoformat() if created_at_dt else ""

    return {
        "id": notif.id,
        "title": notif.title,
        "message": notif.message,
        "type": notif.type,
        "applicationId": notif.application_id,
        "application_id": notif.application_id,
        "read": bool(notif.read),
        "date": date_str,
        "created_at": iso_str,
    }


def list_notifications_controller(
    user: User,
    db: Session,
    unread_only: bool = False,
) -> List[Dict[str, Any]]:
    notifications = service.list_user_notifications(db, user.id, unread_only=unread_only)
    return [_serialize_notification(n) for n in notifications]


def mark_read_controller(
    notification_id: int,
    user: User,
    db: Session,
) -> Dict[str, Any]:
    notif = service.mark_as_read(db, user.id, notification_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return _serialize_notification(notif)


def mark_all_read_controller(
    user: User,
    db: Session,
) -> Dict[str, Any]:
    count = service.mark_all_as_read(db, user.id)
    return {"marked_read_count": count}


def delete_notification_controller(
    notification_id: int,
    user: User,
    db: Session,
) -> Dict[str, Any]:
    deleted = service.delete_notification(db, user.id, notification_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"deleted": True, "id": notification_id}


def create_notification_controller(
    data: CreateNotificationRequest,
    user: User,
    db: Session,
) -> Dict[str, Any]:
    notif = service.create_notification(
        db=db,
        user_id=user.id,
        title=data.title,
        message=data.message,
        notif_type=data.type or "status",
        application_id=data.application_id,
    )
    return _serialize_notification(notif)
