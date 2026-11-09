# ─────────────────────────────────────────────────────────────────────────────
# File    : shared/models/support.py
# Purpose : SQLAlchemy ORM Models for Customer Support Console (sa12, SAP-FR-010)
# ─────────────────────────────────────────────────────────────────────────────

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from shared.database.base import Base, TimestampMixin


class SupportTicket(Base, TimestampMixin):
    """
    Support case queue model fulfilling SAP-FR-010 and LV-BRD-REQ-0034.
    Maintains deep linkage to users, companies, and jobs for instant context.
    """
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String(50), unique=True, nullable=False, index=True)

    subject = Column(String(255), nullable=False)
    # Category: ACCOUNT, BILLING, TECHNICAL, CONTENT, OTHER
    category = Column(String(50), nullable=False, default="ACCOUNT", index=True)
    # Priority: LOW, MEDIUM, HIGH, URGENT
    priority = Column(String(20), nullable=False, default="MEDIUM", index=True)
    # Status: OPEN, IN_PROGRESS, RESOLVED, CLOSED
    status = Column(String(30), nullable=False, default="OPEN", index=True)

    # Submitter identity & role
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    submitter_name = Column(String(255), nullable=False)
    submitter_email = Column(String(255), nullable=False, index=True)
    submitter_role = Column(String(50), nullable=False, default="JOBSEEKER")  # JOBSEEKER, EMPLOYER, RECRUITER, GUEST

    # Linked Entities for Zero-Switch Context (SAP-FR-010)
    company_id = Column(Integer, ForeignKey("company_profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    job_id = Column(Integer, ForeignKey("job_postings.id", ondelete="SET NULL"), nullable=True, index=True)

    # Resolution & Admin Assignment
    assigned_admin_id = Column(Integer, ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True)
    resolution_note = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(255), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    company = relationship("CompanyProfile", foreign_keys=[company_id])
    job = relationship("JobPosting", foreign_keys=[job_id])
    assigned_admin = relationship("AdminUser", foreign_keys=[assigned_admin_id])
    messages = relationship("SupportTicketMessage", back_populates="ticket", cascade="all, delete-orphan", order_by="SupportTicketMessage.created_at.asc()")


class SupportTicketMessage(Base):
    """
    Threaded message item and internal-only note for a support ticket.
    """
    __tablename__ = "support_ticket_messages"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True)

    sender_type = Column(String(30), nullable=False)  # USER, ADMIN, SYSTEM
    sender_name = Column(String(255), nullable=False)
    sender_email = Column(String(255), nullable=True)

    message_body = Column(Text, nullable=False)
    is_internal_note = Column(Boolean, default=False, nullable=False)  # True for admin-only notes

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    ticket = relationship("SupportTicket", back_populates="messages")

