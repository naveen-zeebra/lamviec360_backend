from typing import Optional, List
from pydantic import BaseModel


class DashboardSummarySchema(BaseModel):
    total_users: int
    active_users: int
    total_companies: int
    pending_companies: int
    total_jobseekers: int
    total_jobs: int
    active_jobs: int
    pending_job_approvals: int
    total_applications: int
    totalUsers: int
    totalRoles: int
    activeSessions: int
    systemHealth: str


class GrowthMetricsSchema(BaseModel):
    months: List[str]
    user_signups: List[int]
    job_postings: List[int]
    applications: List[int]


class ActivityItemSchema(BaseModel):
    id: int
    user_email: str
    action: str
    module: str
    description: Optional[str] = None
    created_at: Optional[str] = None
