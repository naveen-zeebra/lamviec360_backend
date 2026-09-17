import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, Enum as SQLEnum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.enums import JobStatus


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=lambda: f"JOB-{uuid.uuid4().hex[:6].upper()}")
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    creator_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    department = Column(String(100), nullable=True, default="")
    type = Column(String(100), nullable=False, default="Full-time")
    location = Column(String(255), nullable=False, default="Ho Chi Minh City")
    salary_min = Column(String(50), nullable=True)
    salary_max = Column(String(50), nullable=True)
    negotiable = Column(Boolean, default=False, nullable=False)
    jd = Column(Text, nullable=False)
    skills = Column(JSON, nullable=True, default=list)
    experience = Column(String(50), nullable=True, default="")
    education = Column(String(100), nullable=True, default="")
    deadline = Column(DateTime, nullable=True)
    vacancies = Column(Integer, default=1, nullable=False)
    documents = Column(JSON, nullable=True, default=lambda: ["CV / Resume"])
    status = Column(SQLEnum(JobStatus), nullable=False, default=JobStatus.DRAFT, index=True)
    ai_generated = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    company = relationship("Company", back_populates="jobs")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
