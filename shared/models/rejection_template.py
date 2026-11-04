# ─────────────────────────────────────────────────────────────────────────────
# File    : shared/models/rejection_template.py
# Purpose : SQLAlchemy ORM Model for Company Rejection Templates (EMP-FR-025b)
# ─────────────────────────────────────────────────────────────────────────────

from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from shared.database.base import Base, TimestampMixin


class CompanyRejectionTemplate(Base, TimestampMixin):
    __tablename__ = "company_rejection_templates"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("company_profiles.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    reason_code = Column(String(50), nullable=False, default="qualifications")  # role_filled, qualifications, timing, other
    subject = Column(String(255), nullable=False)
    body_text = Column(Text, nullable=False)
    language = Column(String(10), default="vi", nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)

    # Relationships
    company = relationship("CompanyProfile")

