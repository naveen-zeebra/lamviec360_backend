from typing import Optional
from pydantic import BaseModel


class JobApplicationCreateRequest(BaseModel):
    job_id: int
    cover_letter: Optional[str] = None
    resume_url: Optional[str] = None
