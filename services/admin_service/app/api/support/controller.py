# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/support/controller.py
# Purpose : Controller layer for Support Console with Audit Logging
# ─────────────────────────────────────────────────────────────────────────────

from typing import Dict, Any, Optional
from fastapi import Request
from sqlalchemy.orm import Session

from shared.models import AdminUser, User, SupportTicket, SupportTicketMessage
from shared.utils import log_audit_event
from .schemas import (
    SupportStatusUpdate,
    SupportMessageCreate,
    SupportTicketDetailResponse,
    SupportTicketCreateRequest,
)
from . import service


def list_support_tickets_controller(
    db: Session,
    page: int = 1,
    page_size: int = 15,
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
) -> Dict[str, Any]:
    service.seed_demo_support_cases_if_empty(db)
    return service.list_support_tickets(
        db,
        page=page,
        page_size=page_size,
        search=search,
        status_filter=status_filter,
        category_filter=category_filter,
        priority_filter=priority_filter,
    )


def get_support_ticket_detail_controller(
    db: Session,
    ticket_id: int,
) -> SupportTicketDetailResponse:
    return service.get_support_ticket_detail(db, ticket_id)


def add_ticket_message_controller(
    db: Session,
    ticket_id: int,
    payload: SupportMessageCreate,
    admin_user: AdminUser,
    request: Request,
) -> SupportTicketMessage:
    msg = service.add_ticket_message(db, ticket_id, payload, admin_user)

    action_name = "ADD_INTERNAL_NOTE" if payload.is_internal_note else "REPLY_SUPPORT_TICKET"
    log_audit_event(
        db,
        action=action_name,
        module="GOVERNANCE",
        description=f"Admin {admin_user.email} added {'internal note' if payload.is_internal_note else 'message'} to ticket #{ticket_id}",
        user_id=admin_user.id,
        user_email=admin_user.email,
        user_type="admin",
        request=request,
        details={"ticket_id": ticket_id, "is_internal_note": payload.is_internal_note},
    )
    return msg


def update_ticket_status_controller(
    db: Session,
    ticket_id: int,
    payload: SupportStatusUpdate,
    admin_user: AdminUser,
    request: Request,
) -> SupportTicket:
    ticket = service.update_ticket_status(db, ticket_id, payload, admin_user)

    log_audit_event(
        db,
        action="UPDATE_SUPPORT_STATUS",
        module="GOVERNANCE",
        description=f"Admin {admin_user.email} changed ticket #{ticket.ticket_number} status to {payload.status}",
        user_id=admin_user.id,
        user_email=admin_user.email,
        user_type="admin",
        request=request,
        details={
            "ticket_id": ticket.id,
            "ticket_number": ticket.ticket_number,
            "new_status": payload.status,
            "resolution_note": payload.resolution_note,
        },
    )
    return ticket


def create_support_ticket_controller(
    db: Session,
    payload: SupportTicketCreateRequest,
    current_user: Optional[User] = None,
) -> SupportTicket:
    user_id = current_user.id if current_user else None
    return service.create_support_ticket(db, payload, user_id=user_id)

