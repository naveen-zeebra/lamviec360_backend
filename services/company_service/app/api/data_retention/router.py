from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from shared.database.session import get_db
from shared.models import User, CompanyProfile, JobPosting, JobApplication
from shared.schemas import APIResponse
from shared.utils import require_user_type, success_response

router = APIRouter(prefix="/data-retention", tags=["Data Retention"])

def _get_company_tenant(user: User) -> CompanyProfile:
    profile = user.company_profile
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted: No employer organization associated with this tenant account",
        )
    return profile

@router.post("/purge", response_model=APIResponse[dict])
def purge_company_data(
    months: int = Query(6, ge=1),
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = _get_company_tenant(user)
    cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)

    # Strictly purge applications belonging ONLY to this company tenant's jobs
    matching_apps = (
        db.query(JobApplication.id)
        .join(JobPosting, JobApplication.job_id == JobPosting.id)
        .filter(
            JobPosting.company_id == profile.id,
            JobApplication.created_at < cutoff,
            JobApplication.status.in_(["rejected", "withdrawn"])
        )
        .all()
    )
    ids_to_purge = [r[0] for r in matching_apps]

    deleted_count = 0
    if ids_to_purge:
        deleted_count = (
            db.query(JobApplication)
            .filter(JobApplication.id.in_(ids_to_purge))
            .delete(synchronize_session=False)
        )
        db.commit()

    return success_response(
        data={"purged_count": deleted_count},
        message=f"Purged {deleted_count} candidate records older than {months} months for company {profile.company_name}."
    )
