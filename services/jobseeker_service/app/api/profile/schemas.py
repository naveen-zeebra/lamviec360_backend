from typing import Optional
from pydantic import BaseModel, field_validator


class JobSeekerProfileUpdateSchema(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    headline: Optional[str] = None
    bio: Optional[str] = None
    resume_url: Optional[str] = None
    skills: Optional[str] = None
    experience_years: Optional[float] = None
    expected_salary: Optional[float] = None
    city: Optional[str] = None
    country: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    # BR-101-07: Profile Visibility
    is_visible: Optional[bool] = None
    visibility: Optional[str] = None

    @field_validator("expected_salary")
    @classmethod
    def validate_expected_salary(cls, v: Optional[float]) -> Optional[float]:
        # BR-101-05: Salary Expectation 1M - 500M VND
        if v is not None:
            if v < 1_000_000 or v > 500_000_000:
                raise ValueError("Salary expectations must be within the range of 1M–500M VND per month (1,000,000 to 500,000,000 VND).")
        return v

    class Config:
        extra = "allow"
