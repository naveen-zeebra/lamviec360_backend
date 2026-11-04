# ─────────────────────────────────────────────────────────────────────────────
# File    : shared/models/notification_preference.py
# Purpose : SQLAlchemy ORM Model for User Notification Preferences (NTF-FR-005)
# ─────────────────────────────────────────────────────────────────────────────

from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from shared.database.base import Base, TimestampMixin


class NotificationPreference(Base, TimestampMixin):
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # Job Seeker email preferences (NTF-FR-005 / js13)
    email_job_recommendations = Column(Boolean, default=True, nullable=False)
    email_application_updates = Column(Boolean, default=True, nullable=False)
    email_interview_alerts = Column(Boolean, default=True, nullable=False)
    email_marketing = Column(Boolean, default=False, nullable=False)

    # In-app notification delivery (NTF-FR-003)
    in_app_enabled = Column(Boolean, default=True, nullable=False)

    # Recruiter / Employer email preferences (EMP-FR-025 / e18)
    email_new_applications = Column(Boolean, default=True, nullable=False)
    email_interview_reminders = Column(Boolean, default=True, nullable=False)
    email_team_activity = Column(Boolean, default=True, nullable=False)
    email_billing = Column(Boolean, default=True, nullable=False)

    # Relationship
    user = relationship("User", back_populates="notification_preferences")

