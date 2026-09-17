import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Enum as SQLEnum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.enums import InterviewMode, InterviewStatus


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(String(36), primary_key=True, default=lambda: f"INT-{uuid.uuid4().hex[:6].upper()}")
    application_id = Column(String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    round_name = Column(String(255), nullable=False, default="First round – Technical")
    scheduled_at = Column(DateTime, nullable=False)
    duration_min = Column(Integer, default=45, nullable=False)
    mode = Column(SQLEnum(InterviewMode), default=InterviewMode.VIDEO, nullable=False)
    location_or_link = Column(String(500), nullable=True, default="")
    instructions = Column(Text, nullable=True, default="")
    interviewers = Column(JSON, nullable=True, default=list)
    documents = Column(JSON, nullable=True, default=lambda: ["CV / Resume"])
    status = Column(SQLEnum(InterviewStatus), default=InterviewStatus.INVITED, nullable=False)
    response_note = Column(Text, nullable=True)
    response_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    application = relationship("Application", back_populates="interview")
