# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/notifications/service.py
# Purpose : Business logic for Job Seeker Notifications
# ─────────────────────────────────────────────────────────────────────────────

from typing import List, Optional
from sqlalchemy.orm import Session
from shared.models.notification import Notification


def list_user_notifications(
    db: Session,
    user_id: int,
    unread_only: bool = False,
) -> List[Notification]:
    """Retrieve notifications belonging to a specific user ordered newest first."""
    query = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        query = query.filter(Notification.read == False)
    return query.order_by(Notification.created_at.desc()).all()


def mark_as_read(
    db: Session,
    user_id: int,
    notification_id: int,
) -> Optional[Notification]:
    """Mark a single notification as read if it belongs to the user."""
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .first()
    )
    if not notif:
        return None
    notif.read = True
    db.commit()
    db.refresh(notif)
    return notif


def mark_all_as_read(db: Session, user_id: int) -> int:
    """Mark all unread notifications as read for the user."""
    updated = (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.read == False)
        .update({"read": True}, synchronize_session=False)
    )
    db.commit()
    return updated


def delete_notification(db: Session, user_id: int, notification_id: int) -> bool:
    """Delete a notification belonging to the user."""
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .first()
    )
    if not notif:
        return False
    db.delete(notif)
    db.commit()
    return True


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    notif_type: str = "status",
    application_id: Optional[int] = None,
) -> Notification:
    """Create and persist a new notification for a user."""
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notif_type,
        application_id=application_id,
        read=False,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif
