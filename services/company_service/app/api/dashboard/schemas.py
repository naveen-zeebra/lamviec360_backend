from typing import Optional, List
from pydantic import BaseModel


class DashboardMetricsSchema(BaseModel):
    active_jobs: int
    total_jobs: int
    total_candidates: int
    interviews_scheduled: int
    new_messages: int = 0


class QuotaSchema(BaseModel):
    plan: str
    limit: int
    used: int
    remaining: int


class RecentApplicationSchema(BaseModel):
    id: int
    job_id: int
    job_title: str
    candidate_name: str
    candidate_email: str
    status: str
    applied_at: Optional[str] = None


class CompanyDashboardResponseSchema(BaseModel):
    metrics: DashboardMetricsSchema
    quota: QuotaSchema
    recent_applications: List[RecentApplicationSchema]
