import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class SeekerProfile(Base):
    __tablename__ = "seeker_profiles"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    phone = Column(String(50), nullable=True, default="")
    location = Column(String(255), nullable=True, default="")
    title = Column(String(255), nullable=True, default="")
    experience_years = Column(String(50), nullable=True, default="")
    industry = Column(String(100), nullable=True, default="")
    skills = Column(JSON, nullable=True, default=list)
    languages = Column(JSON, nullable=True, default=list)
    education = Column(JSON, nullable=True, default=list)
    experience = Column(JSON, nullable=True, default=list)
    resume_file_name = Column(String(255), nullable=True, default="")
    resume_url = Column(String(500), nullable=True, default="")
    resume_size = Column(Integer, nullable=True, default=0)
    resume_uploaded_at = Column(DateTime, nullable=True)
    preferences = Column(JSON, nullable=True, default=dict)
    privacy_settings = Column(JSON, nullable=True, default=dict)

    user = relationship("User", back_populates="seeker_profile")


class SavedJob(Base):
    __tablename__ = "saved_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
