from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc

from shared.database.session import get_db
from shared.models import User, CompanyProfile, JobPosting, JobApplication, JobSeekerProfile
from shared.schemas import ApplicationStatusUpdate, PaginatedResponse, APIResponse
from shared.utils import (
    get_current_user,
    require_user_type,
    success_response,
    paginated_response,
    log_audit_event,
)

router = APIRouter(prefix="/applicants", tags=["ATS Applicant Management"])

@router.get("", response_model=PaginatedResponse[dict])
def list_applicants(
    job_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = user.company_profile
    if not profile:
        return paginated_response(items=[], total_items=0, page=page, page_size=page_size)

    # Query applications for any job posted by this company
    query = (
        db.query(JobApplication)
        .join(JobPosting, JobApplication.job_id == JobPosting.id)
        .filter(JobPosting.company_id == profile.id, JobPosting.is_deleted == False)
    )

    if job_id:
        query = query.filter(JobApplication.job_id == job_id)
    if status_filter:
        query = query.filter(JobApplication.status == status_filter)

    total_items = query.count()
    offset = (page - 1) * page_size
    applications = query.order_by(desc(JobApplication.created_at)).offset(offset).limit(page_size).all()

    items = []
    for app in applications:
        seeker = app.jobseeker
        seeker_user = seeker.user if seeker else None
        items.append({
            "id": app.id,
            "job_id": app.job_id,
            "job_title": app.job.title if app.job else "Unknown Job",
            "candidate_name": seeker_user.full_name if seeker_user else "Anonymous",
            "candidate_email": seeker_user.email if seeker_user else None,
            "candidate_phone": seeker_user.phone if seeker_user else None,
            "candidate_headline": seeker.headline if seeker else None,
            "candidate_skills": seeker.skills if seeker else None,
            "candidate_experience_years": float(seeker.experience_years or 0) if seeker else 0.0,
            "resume_url": app.resume_url or (seeker.resume_url if seeker else None),
            "cover_letter": app.cover_letter,
            "status": app.status,
            "rating": app.rating,
            "recruiter_notes": app.recruiter_notes,
            "applied_at": app.created_at,
        })

    return paginated_response(
        items=items,
        total_items=total_items,
        page=page,
        page_size=page_size,
        message="Applicants retrieved",
    )


@router.get("/{application_id}", response_model=APIResponse[dict])
def get_applicant_detail(
    application_id: int,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = user.company_profile
    app = (
        db.query(JobApplication)
        .join(JobPosting, JobApplication.job_id == JobPosting.id)
        .filter(JobApplication.id == application_id, JobPosting.company_id == profile.id if profile else False)
        .first()
    )

    if not app:
        raise HTTPException(status_code=404, detail="Applicant record not found")

    seeker = app.jobseeker
    seeker_user = seeker.user if seeker else None

    return success_response(
        data={
            "id": app.id,
            "job_id": app.job_id,
            "job_title": app.job.title if app.job else "",
            "status": app.status,
            "rating": app.rating,
            "recruiter_notes": app.recruiter_notes,
            "cover_letter": app.cover_letter,
            "resume_url": app.resume_url,
            "applied_at": app.created_at,
            "updated_at": app.updated_at,
            "candidate": {
                "name": seeker_user.full_name if seeker_user else "",
                "email": seeker_user.email if seeker_user else "",
                "phone": seeker_user.phone if seeker_user else "",
                "headline": seeker.headline if seeker else "",
                "bio": seeker.bio if seeker else "",
                "skills": seeker.skills if seeker else "",
                "experience_years": float(seeker.experience_years or 0) if seeker else 0.0,
                "city": seeker.city if seeker else "",
                "country": seeker.country if seeker else "",
                "github_url": seeker.github_url if seeker else "",
                "linkedin_url": seeker.linkedin_url if seeker else "",
            } if seeker else None,
        }
    )


@router.patch("/{application_id}/status", response_model=APIResponse[dict])
def update_applicant_status(
    application_id: int,
    data: ApplicationStatusUpdate,
    request: Request,
    user: User = Depends(require_user_type("company", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = user.company_profile
    app = (
        db.query(JobApplication)
        .join(JobPosting, JobApplication.job_id == JobPosting.id)
        .filter(JobApplication.id == application_id, JobPosting.company_id == profile.id if profile else False)
        .first()
    )

    if not app:
        raise HTTPException(status_code=404, detail="Applicant record not found")

    app.status = data.status
    if data.recruiter_notes is not None:
        app.recruiter_notes = data.recruiter_notes
    if data.rating is not None:
        app.rating = data.rating

    db.commit()

    log_audit_event(
        db,
        action="UPDATE_APPLICANT_STATUS",
        module="ATS",
        description=f"Candidate application {application_id} updated to status '{data.status}'",
        user_id=user.id,
        user_email=user.email,
        user_type=user.user_type,
        request=request,
    )

    return success_response(
        data={"id": app.id, "status": app.status, "rating": app.rating},
        message="Applicant status updated successfully",
    )
