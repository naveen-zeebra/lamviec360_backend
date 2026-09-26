from sqlalchemy import Column, Integer, String, Text, ForeignKey, Numeric, Boolean, DateTime
from sqlalchemy.orm import relationship
from shared.database.base import Base, TimestampMixin, SoftDeleteMixin

class JobPosting(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "job_postings"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("company_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=True)
    benefits = Column(Text, nullable=True)
    
    job_type = Column(String(50), default="Full-time", nullable=False)  # Full-time, Part-time, Contract, Internship
    workplace_type = Column(String(50), default="On-site", nullable=False)  # On-site, Hybrid, Remote
    experience_level = Column(String(50), default="Mid-level", nullable=True)  # Junior, Mid-level, Senior, Lead
    
    city = Column(String(100), nullable=True, index=True)
    country = Column(String(100), default="Vietnam")
    
    salary_min = Column(Numeric(12, 2), nullable=True)
    salary_max = Column(Numeric(12, 2), nullable=True)
    salary_currency = Column(String(10), default="USD")
    is_negotiable = Column(Boolean, default=False)
    
    required_skills = Column(Text, nullable=True)  # Comma separated e.g. "React, Python, Docker"
    
    # Status lifecycle
    status = Column(String(50), default="published", nullable=False, index=True)  # draft, published, closed
    moderation_status = Column(String(50), default="approved", nullable=False, index=True)  # pending, approved, rejected
    moderation_notes = Column(Text, nullable=True)
    
    views_count = Column(Integer, default=0)
    applications_count = Column(Integer, default=0)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    company = relationship("CompanyProfile", back_populates="job_postings")
    applications = relationship("JobApplication", back_populates="job", cascade="all, delete-orphan")
