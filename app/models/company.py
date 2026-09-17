import uuid
from datetime import datetime, timedelta
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.enums import CompanyApprovalStatus, UserRole


class Company(Base):
    __tablename__ = "companies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    reg_number = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=False)
    size = Column(String(50), nullable=False)
    website = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    logo = Column(String(500), nullable=True)
    approval_status = Column(SQLEnum(CompanyApprovalStatus), nullable=False, default=CompanyApprovalStatus.PENDING)
    verified = Column(Boolean, default=False, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    rejection_reason = Column(Text, nullable=True)
    suspend_reason = Column(Text, nullable=True)
    plan_id = Column(String(50), default="Freemium", nullable=False)
    settings = Column(JSON, nullable=True, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    members = relationship("User", back_populates="company", foreign_keys="User.company_id")
    jobs = relationship("Job", back_populates="company", cascade="all, delete-orphan")
    invitations = relationship("CompanyInvitation", back_populates="company", cascade="all, delete-orphan")


class CompanyInvitation(Base):
    __tablename__ = "company_invitations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.COMPANY_HR)
    invite_token = Column(String(100), unique=True, index=True, nullable=False)
    message = Column(String(500), nullable=True, default="")
    status = Column(String(50), default="Pending", nullable=False)
    sent_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    expiry = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=7), nullable=False)

    company = relationship("Company", back_populates="invitations")
