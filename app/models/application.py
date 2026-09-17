import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, Enum as SQLEnum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.enums import ApplicationStage


class Application(Base):
    __tablename__ = "applications"

    id = Column(String(36), primary_key=True, default=lambda: f"APP-{uuid.uuid4().hex[:6].upper()}")
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    seeker_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    stage = Column(SQLEnum(ApplicationStage), nullable=False, default=ApplicationStage.APPLIED, index=True)
    match_score = Column(Integer, default=70, nullable=False)
    resume_file_name = Column(String(255), nullable=True)
    resume_url = Column(String(500), nullable=True)
    cover_letter = Column(Text, nullable=True)
    answers = Column(JSON, nullable=True, default=dict)
    rejection_template_id = Column(String(50), nullable=True)
    rejection_note = Column(Text, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    applied_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed = Column(Boolean, default=False, nullable=False)

    # Relationships
    job = relationship("Job", back_populates="applications")
    seeker = relationship("User", back_populates="applications")
    notes = relationship("ApplicationNote", back_populates="application", cascade="all, delete-orphan")
    timeline = relationship("ApplicationTimeline", back_populates="application", cascade="all, delete-orphan")
    interview = relationship("Interview", back_populates="application", uselist=False, cascade="all, delete-orphan")


class ApplicationNote(Base):
    __tablename__ = "application_notes"

    id = Column(String(36), primary_key=True, default=lambda: f"NOTE-{uuid.uuid4().hex[:6].upper()}")
    application_id = Column(String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    author = Column(String(255), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    application = relationship("Application", back_populates="notes")


class ApplicationTimeline(Base):
    __tablename__ = "application_timelines"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    stage = Column(SQLEnum(ApplicationStage), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    application = relationship("Application", back_populates="timeline")
