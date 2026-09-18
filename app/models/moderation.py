import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, Enum as SQLEnum, JSON
from app.core.database import Base
from app.models.enums import ModerationType, ModerationStatus


class ModerationItem(Base):
    __tablename__ = "moderation_items"

    id = Column(String(36), primary_key=True, default=lambda: f"MOD-{uuid.uuid4().hex[:6].upper()}")
    type = Column(SQLEnum(ModerationType), nullable=False)
    target_id = Column(String(50), nullable=False)
    target_name = Column(String(255), nullable=False)
    company_id = Column(String(36), nullable=True)
    reason = Column(Text, nullable=False)
    flagged_by = Column(String(100), nullable=False, default="System — keyword filter")
    status = Column(SQLEnum(ModerationStatus), nullable=False, default=ModerationStatus.OPEN)
    target_data = Column(JSON, nullable=True, default=dict)
    flagged_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

