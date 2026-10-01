# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/notifications/router.py
# Purpose : Presentation layer (FastAPI endpoints) for Job Seeker Notifications
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.models import User
from shared.schemas import APIResponse
from shared.utils import get_current_jobseeker, success_response

from .schemas import CreateNotificationRequest
from .controller import (
    list_notifications_controller,
    mark_read_controller,
    mark_all_read_controller,
    delete_notification_controller,
    create_notification_controller,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=APIResponse[list], summary="Get Notifications")
def get_notifications(
    unread_only: bool = Query(default=False, description="Filter only unread notifications"),
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    data = list_notifications_controller(user, db, unread_only=unread_only)
    return success_response(data=data)


@router.patch("/{notification_id}/read", response_model=APIResponse[dict], summary="Mark Notification as Read")
def mark_notification_read(
    notification_id: int,
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    data = mark_read_controller(notification_id, user, db)
    return success_response(data=data, message="Notification marked as read")


@router.patch("/read-all", response_model=APIResponse[dict], summary="Mark All Notifications as Read")
def mark_all_notifications_read(
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    data = mark_all_read_controller(user, db)
    return success_response(data=data, message="All notifications marked as read")


@router.delete("/{notification_id}", response_model=APIResponse[dict], summary="Delete Notification")
def delete_notification(
    notification_id: int,
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    data = delete_notification_controller(notification_id, user, db)
    return success_response(data=data, message="Notification deleted successfully")


@router.post("", response_model=APIResponse[dict], summary="Create Notification")
def create_notification(
    payload: CreateNotificationRequest,
    user: User = Depends(get_current_jobseeker),
    db: Session = Depends(get_db),
):
    data = create_notification_controller(payload, user, db)
    return success_response(data=data, message="Notification created successfully")
