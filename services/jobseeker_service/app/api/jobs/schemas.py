from typing import Optional
from pydantic import BaseModel, Field


class JobSearchParams(BaseModel):
    keyword: Optional[str] = None
    city: Optional[str] = None
    job_type: Optional[str] = None
    workplace_type: Optional[str] = None
    experience_level: Optional[str] = None
    min_salary: Optional[float] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)


class JobReportCreateSchema(BaseModel):
    reason: str = Field(..., description="Category of report: Scam, Fake Salary, Discrimination, Expired, Other")
    details: Optional[str] = Field(None, description="Detailed explanation or evidence")
    reporter_email: Optional[str] = Field(None, description="Contact email of the reporter")
    reporter_name: Optional[str] = Field(None, description="Full name of the reporter")
