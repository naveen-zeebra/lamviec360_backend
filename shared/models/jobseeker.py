from sqlalchemy import Column, Integer, String, Text, ForeignKey, Numeric
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

    # Relationships
    user = relationship("User", back_populates="jobseeker_profile")
    applications = relationship("JobApplication", back_populates="jobseeker", cascade="all, delete-orphan")
    saved_jobs = relationship("SavedJob", back_populates="jobseeker", cascade="all, delete-orphan")


class SavedJob(Base, TimestampMixin):
    __tablename__ = "saved_jobs"

    id = Column(Integer, primary_key=True, index=True)
    jobseeker_id = Column(Integer, ForeignKey("jobseeker_profiles.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(Integer, ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False)

    jobseeker = relationship("JobSeekerProfile", back_populates="saved_jobs")
    job = relationship("JobPosting")
