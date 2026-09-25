from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from shared.database.session import get_db
from shared.models import User, CompanyProfile, JobPosting, JobApplication
from shared.schemas import APIResponse
from shared.utils import get_current_user, require_user_type, success_response

router = APIRouter(prefix="/dashboard", tags=["Company Dashboard"])

def _get_company_tenant(user: User) -> CompanyProfile:
    profile = user.company_profile
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted: No employer organization associated with this tenant account",
        )
    return profile

@router.get("", response_model=APIResponse[dict])
def get_company_dashboard(
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = _get_company_tenant(user)

    total_jobs = db.query(JobPosting).filter(
        JobPosting.company_id == profile.id,
        JobPosting.is_deleted == False
    ).count()

    active_jobs = db.query(JobPosting).filter(
        JobPosting.company_id == profile.id,
        JobPosting.is_deleted == False,
        JobPosting.status.in_(["published", "open", "active", "Published"])
    ).count()

    total_applicants = db.query(JobApplication).join(
        JobPosting, JobApplication.job_id == JobPosting.id
    ).filter(
        JobPosting.company_id == profile.id,
        JobPosting.is_deleted == False
    ).count()

    interviews_scheduled = db.query(JobApplication).join(
        JobPosting, JobApplication.job_id == JobPosting.id
    ).filter(
        JobPosting.company_id == profile.id,
        JobPosting.is_deleted == False,
        JobApplication.status.in_(["interviewing", "interview", "scheduled", "Interview Scheduled"])
    ).count()

    plan_name = (getattr(profile, "subscription_tier", "Freemium") or "Freemium").title()
    limits = {"Freemium": 3, "Professional": 25, "Enterprise": 9999}
    plan_limit = limits.get(plan_name, 3)

    recent_apps_records = (
        db.query(JobApplication)
        .join(JobPosting, JobApplication.job_id == JobPosting.id)
        .filter(JobPosting.company_id == profile.id, JobPosting.is_deleted == False)
        .order_by(JobApplication.created_at.desc())
        .limit(5)
        .all()
    )

    recent_applications = []
    for app in recent_apps_records:
        seeker = app.jobseeker
        seeker_user = seeker.user if seeker else None
        recent_applications.append({
            "id": app.id,
            "job_id": app.job_id,
            "job_title": app.job.title if app.job else "Role",
            "candidate_name": seeker_user.full_name if seeker_user else "Applicant",
            "candidate_email": seeker_user.email if seeker_user else "",
            "status": app.status,
            "applied_at": app.created_at.isoformat() if app.created_at else None,
        })

    return success_response(
        data={
            "metrics": {
                "active_jobs": active_jobs,
                "total_jobs": total_jobs,
                "total_candidates": total_applicants,
                "interviews_scheduled": interviews_scheduled,
                "new_messages": 0,
            },
            "quota": {
                "plan": plan_name,
                "limit": plan_limit,
                "used": total_jobs,
                "remaining": max(0, plan_limit - total_jobs),
            },
            "recent_applications": recent_applications,
        }
    )
