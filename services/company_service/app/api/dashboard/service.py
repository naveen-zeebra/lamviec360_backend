# ─────────────────────────────────────────────────────────────────────────────
# File    : services/company_service/app/api/dashboard/service.py
# Purpose : Domain & aggregation logic for Company Dashboard
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from shared.models import User, CompanyProfile, JobPosting, JobApplication
from shared.utils.error_handler import service_error_handler
from shared.utils.logger import get_logger

logger = get_logger("company_dashboard_service")


@service_error_handler
def get_company_tenant(user: User) -> Optional[CompanyProfile]:
    """Retrieve company profile for user."""
    return user.company_profile


@service_error_handler
def compute_dashboard_metrics(db: Session, company_id: int) -> Dict[str, Any]:
    """Compute active and total job counts, candidate counts, and interview counts."""
    total_jobs = db.query(JobPosting).filter(
        JobPosting.company_id == company_id,
        JobPosting.is_deleted == False,
    ).count()

    active_jobs = db.query(JobPosting).filter(
        JobPosting.company_id == company_id,
        JobPosting.is_deleted == False,
        JobPosting.status.in_(["published", "open", "active", "Published"]),
    ).count()

    total_applicants = db.query(JobApplication).join(
        JobPosting, JobApplication.job_id == JobPosting.id,
    ).filter(
        JobPosting.company_id == company_id,
        JobPosting.is_deleted == False,
    ).count()

    interviews_scheduled = db.query(JobApplication).join(
        JobPosting, JobApplication.job_id == JobPosting.id,
    ).filter(
        JobPosting.company_id == company_id,
        JobPosting.is_deleted == False,
        JobApplication.status.in_(["interviewing", "interview", "scheduled", "Interview Scheduled"]),
    ).count()

    return {
        "active_jobs": active_jobs,
        "total_jobs": total_jobs,
        "total_candidates": total_applicants,
        "interviews_scheduled": interviews_scheduled,
        "new_messages": 0,
    }


def compute_quota_metrics(profile: CompanyProfile, total_jobs: int) -> Dict[str, Any]:
    """Determine plan quota and remaining allowances."""
    plan_name = (getattr(profile, "subscription_tier", "Freemium") or "Freemium").title()
    limits = {"Freemium": 3, "Professional": 25, "Enterprise": 9999}
    plan_limit = limits.get(plan_name, 3)

    return {
        "plan": plan_name,
        "limit": plan_limit,
        "used": total_jobs,
        "remaining": max(0, plan_limit - total_jobs),
    }


@service_error_handler
def get_recent_applications(db: Session, company_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieve most recent applications."""
    records = (
        db.query(JobApplication)
        .join(JobPosting, JobApplication.job_id == JobPosting.id)
        .filter(JobPosting.company_id == company_id, JobPosting.is_deleted == False)
        .order_by(JobApplication.created_at.desc())
        .limit(limit)
        .all()
    )

    recent = []
    for app in records:
        seeker = app.jobseeker
        seeker_user = seeker.user if seeker else None
        recent.append({
            "id": app.id,
            "job_id": app.job_id,
            "job_title": app.job.title if app.job else "Role",
            "candidate_name": seeker_user.full_name if seeker_user else "Applicant",
            "candidate_email": seeker_user.email if seeker_user else "",
            "status": app.status,
            "applied_at": app.created_at.isoformat() if app.created_at else None,
        })
    return recent
