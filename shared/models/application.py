from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from shared.database.base import Base, TimestampMixin

class JobApplication(Base, TimestampMixin):
    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False, index=True)
    jobseeker_id = Column(Integer, ForeignKey("jobseeker_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    cover_letter = Column(Text, nullable=True)
    resume_url = Column(String(500), nullable=True)
    
    # Status ATS Pipeline: applied -> reviewing -> shortlisted -> interview -> hired / rejected
    status = Column(String(50), default="applied", nullable=False, index=True)
    recruiter_notes = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5 candidate score

    # Relationships
    job = relationship("JobPosting", back_populates="applications")
    jobseeker = relationship("JobSeekerProfile", back_populates="applications")
