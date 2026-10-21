from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from shared.database.base import Base, TimestampMixin

class JobApplication(Base, TimestampMixin):
    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False, index=True)
    jobseeker_id = Column(Integer, ForeignKey("jobseeker_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    cover_letter = Column(Text, nullable=True)
    resume_url = Column(String(500), nullable=True)
    resume_name = Column(String(255), nullable=True)
    
    # BR-011: Mandatory candidate data consent
    consent = Column(Boolean, default=True, nullable=False)
    consent_timestamp = Column(DateTime, nullable=True)
    
    # Status ATS Pipeline: applied -> reviewing -> shortlisted -> interview -> hired / rejected
    status = Column(String(50), default="applied", nullable=False, index=True)
    recruiter_notes = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5 candidate score

    # BR-301-11: Talent auto-acknowledgment within 24 hours of submission
    acknowledgment_sent = Column(Boolean, default=False, nullable=True)
    acknowledgment_sent_at = Column(DateTime, nullable=True)

    # Relationships
    job = relationship("JobPosting", back_populates="applications")
    jobseeker = relationship("JobSeekerProfile", back_populates="applications")

