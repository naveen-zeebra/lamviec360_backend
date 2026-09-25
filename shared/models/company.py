from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from shared.database.base import Base, TimestampMixin

class CompanyProfile(Base, TimestampMixin):
    __tablename__ = "company_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    company_name = Column(String(255), nullable=False, index=True)
    legal_name = Column(String(255), nullable=True)
    logo_url = Column(String(500), nullable=True)
    cover_image_url = Column(String(500), nullable=True)
    website = Column(String(255), nullable=True)
    industry = Column(String(100), nullable=True, index=True)
    company_size = Column(String(50), nullable=True)  # e.g. "50-200 employees"
    about = Column(Text, nullable=True)
    address = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), default="Vietnam")
    
    # Extended Company Profile Info
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    contact_person = Column(String(255), nullable=True)
    tax_code = Column(String(100), nullable=True)
    founded_year = Column(Integer, nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    facebook_url = Column(String(500), nullable=True)
    benefits = Column(Text, nullable=True)
    subscription_tier = Column(String(50), default="Freemium", nullable=True)
    settings = Column(Text, nullable=True)  # JSON-encoded tenant settings

    # Moderation & Verification by Super Admin
    verification_status = Column(String(50), default="pending", nullable=False, index=True)  # pending, verified, rejected
    verification_notes = Column(Text, nullable=True)
    is_featured = Column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User", back_populates="company_profile")
    job_postings = relationship("JobPosting", back_populates="company", cascade="all, delete-orphan")
