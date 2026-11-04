# ─────────────────────────────────────────────────────────────────────────────
# File    : shared/models/notification.py
# Purpose : SQLAlchemy ORM Model for User Notifications (FSD-006 Data Entities)
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

    # LV360-FSD-006 Notification delivery & tracking extensions
    channel = Column(String(20), default="in_app", nullable=False)  # email, in_app, sms
    delivery_status = Column(String(20), default="delivered", nullable=False)  # pending, sent, delivered, failed
    scheduled_send_time = Column(DateTime, nullable=True)
    action_url = Column(String(500), nullable=True)
    template_id = Column(String(50), nullable=True)
    language = Column(String(10), default="vi", nullable=False)
