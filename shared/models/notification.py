# ─────────────────────────────────────────────────────────────────────────────
# File    : shared/models/notification.py
# Purpose : SQLAlchemy ORM Model for User Notifications
# ─────────────────────────────────────────────────────────────────────────────

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from shared.database.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default="status", nullable=False)  # confirmation, cv_view, status, interview, offer
    application_id = Column(Integer, nullable=True)
    read = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
