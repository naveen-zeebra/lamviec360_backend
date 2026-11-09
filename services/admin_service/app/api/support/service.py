# ─────────────────────────────────────────────────────────────────────────────
# File    : services/admin_service/app/api/support/service.py
# Purpose : Business logic for Support Console (sa12, SAP-FR-010)
# ─────────────────────────────────────────────────────────────────────────────

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc

from shared.models import SupportTicket, SupportTicketMessage, User, CompanyProfile, JobPosting, AdminUser
from .schemas import (
    SupportTicketCreateRequest,
    SupportStatusUpdate,
    SupportMessageCreate,
    SupportTicketListItem,
    SupportTicketDetailResponse,
    LinkedEntityInfo,
    SupportTicketTrackResponse,
    SupportMessageResponse,
    SupportCustomerReplyRequest,
)


def _generate_ticket_number() -> str:
    now_str = datetime.utcnow().strftime("%Y%m")
    unique_suffix = uuid.uuid4().hex[:6].upper()
    return f"TK-{now_str}-{unique_suffix}"


def list_support_tickets(
    db: Session,
    page: int = 1,
    page_size: int = 15,
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve filtered list of support tickets with pagination and summary counts."""
    query = db.query(SupportTicket)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                SupportTicket.ticket_number.ilike(s),
                SupportTicket.subject.ilike(s),
                SupportTicket.submitter_name.ilike(s),
                SupportTicket.submitter_email.ilike(s),
            )
        )

    if status_filter and status_filter != "ALL":
        query = query.filter(SupportTicket.status == status_filter)

    if category_filter and category_filter != "ALL":
        query = query.filter(SupportTicket.category == category_filter)

    if priority_filter and priority_filter != "ALL":
        query = query.filter(SupportTicket.priority == priority_filter)

    total_items = query.count()
    total_pages = max(1, (total_items + page_size - 1) // page_size) if total_items > 0 else 1

    tickets = (
        query.order_by(
            # Sort open and in_progress first, then newest
            desc(SupportTicket.created_at)
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Compute quick stats
    open_count = db.query(SupportTicket).filter(SupportTicket.status == "OPEN").count()
    in_progress_count = db.query(SupportTicket).filter(SupportTicket.status == "IN_PROGRESS").count()
    resolved_count = db.query(SupportTicket).filter(SupportTicket.status.in_(["RESOLVED", "CLOSED"])).count()

    items: List[SupportTicketListItem] = []
    for t in tickets:
        company_name = t.company.company_name if t.company else None
        job_title = t.job.title if t.job else None
        assigned_name = f"{t.assigned_admin.first_name} {t.assigned_admin.last_name}" if t.assigned_admin else None

        items.append(
            SupportTicketListItem(
                id=t.id,
                ticket_number=t.ticket_number,
                subject=t.subject,
                category=t.category,
                priority=t.priority,
                status=t.status,
                submitter_name=t.submitter_name,
                submitter_email=t.submitter_email,
                submitter_role=t.submitter_role,
                company_name=company_name,
                company_id=t.company_id,
                job_title=job_title,
                job_id=t.job_id,
                assigned_admin_name=assigned_name,
                message_count=len(t.messages),
                created_at=t.created_at,
                updated_at=t.updated_at,
                resolved_at=t.resolved_at,
            )
        )

    return {
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
        },
        "stats": {
            "total": total_items,
            "open": open_count,
            "in_progress": in_progress_count,
            "resolved": resolved_count,
        },
    }


def get_support_ticket_detail(db: Session, ticket_id: int) -> SupportTicketDetailResponse:
    """Retrieve full ticket details with linked entity context (SAP-FR-010)."""
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Support ticket with ID {ticket_id} not found",
        )

    linked = LinkedEntityInfo(
        user_id=ticket.user_id,
        user_name=f"{ticket.user.first_name} {ticket.user.last_name}" if ticket.user else ticket.submitter_name,
        user_email=ticket.user.email if ticket.user else ticket.submitter_email,
        user_role=ticket.user.user_type if ticket.user else ticket.submitter_role,
        company_id=ticket.company_id,
        company_name=ticket.company.company_name if ticket.company else None,
        company_status=ticket.company.verification_status if ticket.company else None,
        company_plan=(ticket.company.subscription_tier or "STANDARD") if ticket.company else None,
        job_id=ticket.job_id,
        job_title=ticket.job.title if ticket.job else None,
        job_status=ticket.job.status if ticket.job else None,
    )

    return SupportTicketDetailResponse(
        id=ticket.id,
        ticket_number=ticket.ticket_number,
        subject=ticket.subject,
        category=ticket.category,
        priority=ticket.priority,
        status=ticket.status,
        submitter_name=ticket.submitter_name,
        submitter_email=ticket.submitter_email,
        submitter_role=ticket.submitter_role,
        resolution_note=ticket.resolution_note,
        resolved_at=ticket.resolved_at,
        resolved_by=ticket.resolved_by,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        linked_record=linked,
        messages=ticket.messages,
    )


def add_ticket_message(
    db: Session,
    ticket_id: int,
    payload: SupportMessageCreate,
    admin_user: AdminUser,
) -> SupportTicketMessage:
    """Add a message response or internal admin note to ticket."""
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    sender_name = f"{admin_user.first_name} {admin_user.last_name}".strip() or admin_user.email
    message = SupportTicketMessage(
        ticket_id=ticket_id,
        sender_type="ADMIN",
        sender_name=sender_name,
        sender_email=admin_user.email,
        message_body=payload.message_body,
        is_internal_note=payload.is_internal_note,
    )
    db.add(message)

    # Automatically transition OPEN -> IN_PROGRESS on first admin message
    if ticket.status == "OPEN" and not payload.is_internal_note:
        ticket.status = "IN_PROGRESS"

    ticket.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(message)
    return message


def update_ticket_status(
    db: Session,
    ticket_id: int,
    payload: SupportStatusUpdate,
    admin_user: AdminUser,
) -> SupportTicket:
    """Update ticket status and record resolution note if resolved."""
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    old_status = ticket.status
    ticket.status = payload.status
    ticket.updated_at = datetime.utcnow()

    if payload.resolution_note:
        ticket.resolution_note = payload.resolution_note

    if payload.status in ["RESOLVED", "CLOSED"]:
        ticket.resolved_at = datetime.utcnow()
        ticket.resolved_by = f"{admin_user.first_name} {admin_user.last_name}".strip() or admin_user.email

    db.commit()
    db.refresh(ticket)
    return ticket


def create_support_ticket(
    db: Session,
    payload: SupportTicketCreateRequest,
    user_id: Optional[int] = None,
) -> SupportTicket:
    """Submit a support ticket from user or employer portal."""
    # Auto-resolve user_id from payload or submitter email
    resolved_user_id = user_id or getattr(payload, 'user_id', None)
    if not resolved_user_id and payload.submitter_email:
        found_user = db.query(User).filter(User.email.ilike(payload.submitter_email.strip())).first()
        if found_user:
            resolved_user_id = found_user.id

    ticket = SupportTicket(
        ticket_number=_generate_ticket_number(),
        subject=payload.subject,
        category=payload.category.upper(),
        priority=payload.priority.upper(),
        status="OPEN",
        user_id=resolved_user_id,
        submitter_name=payload.submitter_name,
        submitter_email=payload.submitter_email,
        submitter_role=payload.submitter_role.upper(),
        company_id=payload.company_id,
        job_id=payload.job_id,
    )
    db.add(ticket)
    db.flush()

    # Initial user message
    initial_msg = SupportTicketMessage(
        ticket_id=ticket.id,
        sender_type="USER",
        sender_name=payload.submitter_name,
        sender_email=payload.submitter_email,
        message_body=payload.message,
        is_internal_note=False,
    )
    db.add(initial_msg)
    db.commit()
    db.refresh(ticket)
    return ticket


def seed_demo_support_cases_if_empty(db: Session) -> None:
    """Seeds realistic demo cases linking to existing users, companies, and jobs for rich verification."""
    if db.query(SupportTicket).count() > 0:
        return

    company = db.query(CompanyProfile).first()
    job = db.query(JobPosting).first()
    user = db.query(User).first()

    demo_cases = [
        {
            "subject": "Inquiry regarding Enterprise plan custom posting quota",
            "category": "BILLING",
            "priority": "HIGH",
            "status": "OPEN",
            "submitter_name": "Nguyen Van Binh",
            "submitter_email": "hr@fptsoftware.vn",
            "submitter_role": "EMPLOYER",
            "company_id": company.id if company else None,
            "job_id": None,
            "message": "Hello LàmViệc360 support, our hiring team is ramping up for Q1 2027 and we'd like to assign custom quotas for our 3 tech subsidiaries under one parent billing profile. Could you guide us on setup?",
        },
        {
            "subject": "Candidate reported salary mismatch on job posting",
            "category": "CONTENT",
            "priority": "URGENT",
            "status": "IN_PROGRESS",
            "submitter_name": "Tran Thi Mai",
            "submitter_email": "mai.tran@gmail.com",
            "submitter_role": "JOBSEEKER",
            "company_id": company.id if company else None,
            "job_id": job.id if job else None,
            "message": "The posting specifies 40M - 50M VND Gross, but after the phone screening the recruiter mentioned 25M VND Base. Please verify if the listing adheres to LàmViệc360 genuine opportunities rule.",
        },
        {
            "subject": "Unable to verify company business registration certificate",
            "category": "ACCOUNT",
            "priority": "MEDIUM",
            "status": "OPEN",
            "submitter_name": "Le Hoang Nam",
            "submitter_email": "admin@vng-corp.vn",
            "submitter_role": "EMPLOYER",
            "company_id": company.id if company else None,
            "job_id": None,
            "message": "We uploaded our updated PDF business license during re-verification but received a format warning. Could support review our uploaded documents in the tenant panel?",
        },
        {
            "subject": "AI resume parsing failed for multi-column German CV",
            "category": "TECHNICAL",
            "priority": "LOW",
            "status": "RESOLVED",
            "submitter_name": "Pham Minh Tu",
            "submitter_email": "tu.pham@outlook.com",
            "submitter_role": "JOBSEEKER",
            "company_id": None,
            "job_id": None,
            "message": "My resume uploaded properly but skill extraction only picked up 2 out of 8 skills because of custom column formatting.",
        },
    ]

    for item in demo_cases:
        create_support_ticket(
            db,
            SupportTicketCreateRequest(
                subject=item["subject"],
                category=item["category"],
                priority=item["priority"],
                message=item["message"],
                submitter_name=item["submitter_name"],
                submitter_email=item["submitter_email"],
                submitter_role=item["submitter_role"],
                company_id=item["company_id"],
                job_id=item["job_id"],
            ),
            user_id=user.id if user else None,
        )



def track_support_ticket(db: Session, ticket_number: str) -> SupportTicketTrackResponse:
    """Retrieve ticket and public message thread for customer/employer tracking."""
    ticket = db.query(SupportTicket).filter(SupportTicket.ticket_number == ticket_number.strip()).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ticket {ticket_number} not found")

    # Filter out internal notes: customer only sees USER messages and public ADMIN replies
    public_messages = [
        SupportMessageResponse.from_orm(m)
        for m in ticket.messages
        if not m.is_internal_note
    ]

    return SupportTicketTrackResponse(
        id=ticket.id,
        ticket_number=ticket.ticket_number,
        subject=ticket.subject,
        category=ticket.category,
        priority=ticket.priority,
        status=ticket.status,
        submitter_name=ticket.submitter_name,
        submitter_email=ticket.submitter_email,
        submitter_role=ticket.submitter_role,
        resolution_note=ticket.resolution_note,
        resolved_at=ticket.resolved_at,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        messages=public_messages,
    )


def customer_reply_to_ticket(db: Session, ticket_number: str, payload: SupportCustomerReplyRequest) -> SupportTicketMessage:
    """Customer or employer appends a follow-up reply to an existing support case."""
    ticket = db.query(SupportTicket).filter(SupportTicket.ticket_number == ticket_number.strip()).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ticket {ticket_number} not found")

    sender_name = payload.submitter_name.strip() if (payload.submitter_name and payload.submitter_name.strip()) else ticket.submitter_name

    msg = SupportTicketMessage(
        ticket_id=ticket.id,
        sender_type="USER",
        sender_name=sender_name,
        sender_email=ticket.submitter_email,
        message_body=payload.message.strip(),
        is_internal_note=False,
    )
    db.add(msg)

    # Reopen ticket to IN_PROGRESS if it was RESOLVED or CLOSED so admins know customer followed up
    if ticket.status in ["RESOLVED", "CLOSED"]:
        ticket.status = "IN_PROGRESS"

    ticket.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(msg)
    return msg


def list_my_support_tickets(
    db: Session,
    email: Optional[str] = None,
    company_id: Optional[int] = None,
    user_id: Optional[int] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Retrieve recent tickets submitted by a specific employer or user."""
    query = db.query(SupportTicket)
    filters = []

    if company_id:
        filters.append(SupportTicket.company_id == company_id)
    if user_id:
        filters.append(SupportTicket.user_id == user_id)
    if email and email.strip():
        filters.append(SupportTicket.submitter_email.ilike(email.strip()))

    if not filters:
        return []

    tickets = query.filter(or_(*filters)).order_by(desc(SupportTicket.created_at)).limit(limit).all()

    result = []
    for t in tickets:
        msgs = [m for m in t.messages if not m.is_internal_note]
        last_msg = msgs[-1] if msgs else None
        has_admin_reply = any(m.sender_type == "ADMIN" for m in msgs)

        result.append({
            "id": t.id,
            "ticket_number": t.ticket_number,
            "subject": t.subject,
            "category": t.category,
            "priority": t.priority,
            "status": t.status,
            "submitter_name": t.submitter_name,
            "submitter_email": t.submitter_email,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            "message_count": len(msgs),
            "has_admin_reply": has_admin_reply,
            "last_message": {
                "sender_type": last_msg.sender_type,
                "sender_name": last_msg.sender_name,
                "message_body": last_msg.message_body[:100] + ("..." if len(last_msg.message_body) > 100 else ""),
                "created_at": last_msg.created_at.isoformat() if last_msg.created_at else None,
            } if last_msg else None,
        })

    return result
