from sqlalchemy import Column, Integer, String, Text, ForeignKey, Numeric, Boolean, DateTime
from sqlalchemy.orm import relationship
from shared.database.base import Base, TimestampMixin

class JobSeekerProfile(Base, TimestampMixin):
    __tablename__ = "jobseeker_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    headline = Column(String(255), nullable=True)  # e.g. "Senior Full-Stack Engineer"
    bio = Column(Text, nullable=True)
    resume_url = Column(String(500), nullable=True)
    skills = Column(Text, nullable=True)  # JSON or comma-delimited strings: "Python, FastAPI, React"
    experience_years = Column(Numeric(4, 1), default=0.0)
    expected_salary = Column(Numeric(12, 2), nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), default="Vietnam")
    github_url = Column(String(255), nullable=True)
    linkedin_url = Column(String(255), nullable=True)

    # BR-101-07: Profile Visibility
    is_visible = Column(Boolean, default=True, nullable=False)
    visibility = Column(String(50), default="public", nullable=False)  # "public", "private"

    # BR-101-08: Inactive Profile Archiving
    is_archived = Column(Boolean, default=False, nullable=False)
    archived_at = Column(DateTime, nullable=True)
    archive_reason = Column(String(255), nullable=True)

    # Relationships
    user = relationship("User", back_populates="jobseeker_profile")
    applications = relationship("JobApplication", back_populates="jobseeker", cascade="all, delete-orphan")
    saved_jobs = relationship("SavedJob", back_populates="jobseeker", cascade="all, delete-orphan")
    resumes = relationship("JobSeekerResume", back_populates="jobseeker", cascade="all, delete-orphan")
    documents = relationship("JobSeekerDocument", back_populates="jobseeker", cascade="all, delete-orphan")


class JobSeekerResume(Base, TimestampMixin):
    __tablename__ = "jobseeker_resumes"

    id = Column(Integer, primary_key=True, index=True)
    jobseeker_id = Column(Integer, ForeignKey("jobseeker_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_name = Column(String(255), nullable=True)  # Named resume title e.g. "Software Engineer CV"
    file_name = Column(String(255), nullable=False)
    file_url = Column(String(500), nullable=False)
    mime_type = Column(String(120), nullable=True)
    size_bytes = Column(Integer, default=0, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)

    jobseeker = relationship("JobSeekerProfile", back_populates="resumes")


class JobSeekerDocument(Base, TimestampMixin):
    """
    JSP-FR-012: Candidate Document Archive.
    Encrypted storage for employment contracts, relieving letters, payslips, and certificates.
    Storage limit: 10MB per file, 100MB quota per candidate.
    """
    __tablename__ = "jobseeker_documents"

    id = Column(Integer, primary_key=True, index=True)
    jobseeker_id = Column(Integer, ForeignKey("jobseeker_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(50), nullable=False, default="other")  # contract, relieving_letter, payslip, certificate, other
    title = Column(String(255), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_url = Column(String(500), nullable=False)
    mime_type = Column(String(120), nullable=True)
    size_bytes = Column(Integer, default=0, nullable=False)

    jobseeker = relationship("JobSeekerProfile", back_populates="documents")


class SavedJob(Base, TimestampMixin):
    __tablename__ = "saved_jobs"

    id = Column(Integer, primary_key=True, index=True)
    jobseeker_id = Column(Integer, ForeignKey("jobseeker_profiles.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(Integer, ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False)

    jobseeker = relationship("JobSeekerProfile", back_populates="saved_jobs")
    job = relationship("JobPosting")

