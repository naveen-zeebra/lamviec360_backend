from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from shared.database.session import get_db
from shared.models import User, JobPosting, JobApplication
from shared.schemas import APIResponse
from shared.utils import get_current_user, require_user_type, success_response

router = APIRouter(prefix="/dashboard", tags=["Company Dashboard"])

@router.get("", response_model=APIResponse[dict])
def get_company_dashboard(
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = user.company_profile
    if not profile:
        return success_response(data={"jobs": 0, "applicants": 0})

    total_jobs = db.query(JobPosting).filter(
        JobPosting.company_id == profile.id,
        JobPosting.is_deleted == False
    ).count()

    total_applicants = db.query(JobApplication).join(
        JobPosting, JobApplication.job_id == JobPosting.id
    ).filter(
        JobPosting.company_id == profile.id,
        JobPosting.is_deleted == False
    ).count()

    return success_response(
        data={
            "metrics": {
                "active_jobs": total_jobs,
                "total_candidates": total_applicants,
                "interviews_scheduled": 0,
                "new_messages": 0
            },
            "recent_applications": []
        }
    )
