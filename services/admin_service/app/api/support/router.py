# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/support/router.py
# Purpose : FastAPI router endpoints for Support Console (sa12, SAP-FR-010)
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from shared.database.session import get_db
from shared.schemas import APIResponse
from shared.utils import require_roles, success_response, paginated_response
from .schemas import (
    SupportStatusUpdate,
    SupportMessageCreate,
    SupportTicketCreateRequest,
    SupportCustomerReplyRequest,
)
from .service import track_support_ticket, customer_reply_to_ticket, list_my_support_tickets
from .controller import (
    list_support_tickets_controller,
    get_support_ticket_detail_controller,
    add_ticket_message_controller,
    update_ticket_status_controller,
    create_support_ticket_controller,
)

router = APIRouter(prefix="/support", tags=["Customer Support Console"])


@router.get("", summary="List Support Cases (Admin)")
def list_support_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin=Depends(require_roles("super_admin", "admin", "compliance_officer", "operations_admin")),
):
    """Retrieve support case queue with status/priority/category filters."""
    res = list_support_tickets_controller(
        db,
        page=page,
        page_size=page_size,
        search=search,
        status_filter=status,
        category_filter=category,
        priority_filter=priority,
    )
    items_data = [item.dict() for item in res["items"]]
    response = paginated_response(
        items=items_data,
        total_items=res["pagination"]["total_items"],
        page=res["pagination"]["page"],
        page_size=res["pagination"]["page_size"],
        message="Support tickets retrieved successfully",
    )
    response["stats"] = res["stats"]
    return response


@router.get("/my-tickets", summary="List My Submitted Tickets (Portal)")
def get_my_tickets(
    email: Optional[str] = Query(None),
    company_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Retrieve recent support tickets for current logged-in employer or seeker."""
    # Attempt to extract user/company info from Authorization header if missing
    if request:
        auth_header = request.headers.get("Authorization") or ""
        if auth_header.startswith("Bearer "):
            raw_token = auth_header[7:].strip()
            try:
                import jwt as pyjwt
                from shared.environment import env
                payload = pyjwt.decode(raw_token, env.JWT_SECRET_KEY, algorithms=[env.JWT_ALGORITHM], options={"verify_exp": False})
                if not email and payload.get("email"):
                    email = payload.get("email")
                sub = payload.get("sub")
                if not user_id and sub and str(sub).isdigit():
                    user_id = int(sub)
                if not company_id and payload.get("company_id"):
                    company_id = int(payload.get("company_id"))
            except Exception:
                pass

    tickets = list_my_support_tickets(
        db,
        email=email,
        company_id=company_id,
        user_id=user_id,
        limit=limit,
    )
    return success_response(data=tickets, message="My tickets retrieved successfully")


@router.get("/{ticket_id}", summary="Get Support Case Detail & Linked Entities")
def get_support_case_detail(
    ticket_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_roles("super_admin", "admin", "compliance_officer", "operations_admin")),
):
    """Retrieve complete support case thread with linked company/user/job record."""
    detail = get_support_ticket_detail_controller(db, ticket_id)
    return success_response(data=detail.dict(), message="Ticket details retrieved")


@router.post("/{ticket_id}/messages", summary="Add Response or Internal Note")
def add_case_message(
    ticket_id: int,
    payload: SupportMessageCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_roles("super_admin", "admin", "compliance_officer", "operations_admin")),
):
    """Post an admin response or internal yellow-accented admin note to the ticket."""
    msg = add_ticket_message_controller(db, ticket_id, payload, admin_user=admin, request=request)
    return success_response(
        data={
            "id": msg.id,
            "ticket_id": msg.ticket_id,
            "sender_type": msg.sender_type,
            "sender_name": msg.sender_name,
            "message_body": msg.message_body,
            "is_internal_note": msg.is_internal_note,
            "created_at": msg.created_at,
        },
        message="Message added successfully",
    )


@router.patch("/{ticket_id}/status", summary="Update Support Case Status")
def update_case_status(
    ticket_id: int,
    payload: SupportStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_roles("super_admin", "admin", "compliance_officer", "operations_admin")),
):
    """Update case lifecycle state (OPEN, IN_PROGRESS, RESOLVED, CLOSED) with audit notes."""
    ticket = update_ticket_status_controller(db, ticket_id, payload, admin_user=admin, request=request)
    return success_response(
        data={"id": ticket.id, "status": ticket.status, "resolved_at": ticket.resolved_at},
        message=f"Ticket status updated to {ticket.status}",
    )


@router.post("/submit", summary="Submit Support Case (Public / Portal)")
def submit_support_case(
    payload: SupportTicketCreateRequest,
    db: Session = Depends(get_db),
):
    """User submission entry point for jobseekers and employers."""
    ticket = create_support_ticket_controller(db, payload)
    return success_response(
        data={"id": ticket.id, "ticket_number": ticket.ticket_number},
        message="Support ticket submitted successfully",
    )



@router.get("/track/{ticket_number}", summary="Track Support Case (Customer / Employer)")
def track_case(
    ticket_number: str,
    db: Session = Depends(get_db),
):
    """Public / portal endpoint for customers and employers to view ticket progress and read admin replies."""
    detail = track_support_ticket(db, ticket_number)
    return success_response(data=detail.dict(), message="Ticket details retrieved")


@router.post("/track/{ticket_number}/reply", summary="Customer Reply to Ticket")
def reply_to_case(
    ticket_number: str,
    payload: SupportCustomerReplyRequest,
    db: Session = Depends(get_db),
):
    """Customer or employer appends a reply message to their open ticket thread."""
    msg = customer_reply_to_ticket(db, ticket_number, payload)
    return success_response(
        data={
            "id": msg.id,
            "ticket_id": msg.ticket_id,
            "sender_type": msg.sender_type,
            "sender_name": msg.sender_name,
            "message_body": msg.message_body,
            "created_at": msg.created_at,
        },
        message="Reply sent successfully",
    )

