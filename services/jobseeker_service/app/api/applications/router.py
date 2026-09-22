from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc

from shared.database.session import get_db
from shared.models import User, JobSeekerProfile, JobPosting, JobApplication
from shared.schemas import ApplicationCreate, APIResponse
from shared.utils import get_current_user, require_user_type, success_response, log_audit_event

router = APIRouter(prefix="/applications", tags=["Job Applications"])

@router.post("", response_model=APIResponse[dict])
def apply_for_job(
    data: ApplicationCreate,
    request: Request,
    user: User = Depends(require_user_type("jobseeker", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = db.query(JobSeekerProfile).filter(JobSeekerProfile.user_id == user.id).first()
    if not profile:
        profile = JobSeekerProfile(user_id=user.id)
        db.add(profile)
        db.flush()

    job = db.query(JobPosting).filter(
        JobPosting.id == data.job_id,
        JobPosting.status == "active",
        JobPosting.is_deleted == False,
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting is no longer active or does not exist")

    # Check duplicate application
    existing = db.query(JobApplication).filter(
        JobApplication.job_id == data.job_id,
        JobApplication.jobseeker_id == profile.id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already applied for this position")

    resume_url = data.resume_url or profile.resume_url

    application = JobApplication(
        job_id=data.job_id,
        jobseeker_id=profile.id,
        cover_letter=data.cover_letter,
        resume_url=resume_url,
        status="applied",
    )
    db.add(application)
    
    # Increment job applications count
    job.applications_count += 1
    db.commit()
    db.refresh(application)

    log_audit_event(
        db,
        action="APPLY",
        module="JOB_APPLICATIONS",
        description=f"User {user.email} applied for job '{job.title}' (ID {job.id})",
        user_id=user.id,
        user_email=user.email,
        user_type=user.user_type,
        request=request,
    )

    return success_response(
        data={
            "application_id": application.id,
            "job_id": job.id,
            "job_title": job.title,
            "status": application.status,
            "applied_at": application.created_at,
        },
        message="Application submitted successfully!",
    )


@router.get("", response_model=APIResponse[list])
def get_my_applications(
    user: User = Depends(require_user_type("jobseeker", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = db.query(JobSeekerProfile).filter(JobSeekerProfile.user_id == user.id).first()
    if not profile:
        return success_response(data=[])

    applications = (
        db.query(JobApplication)
        .filter(JobApplication.jobseeker_id == profile.id)
        .order_by(desc(JobApplication.created_at))
        .all()
    )

    results = []
    for app in applications:
        results.append({
            "id": app.id,
            "status": app.status,
            "applied_at": app.created_at,
            "recruiter_notes": app.recruiter_notes,
            "job": {
                "id": app.job.id,
                "title": app.job.title,
                "job_type": app.job.job_type,
                "city": app.job.city,
                "company_name": app.job.company.company_name if app.job.company else "Unknown",
                "company_logo": app.job.company.logo_url if app.job.company else None,
            } if app.job else None,
        })

    return success_response(data=results)


@router.get("/{application_id}", response_model=APIResponse[dict])
def get_application_detail(
    application_id: int,
    user: User = Depends(require_user_type("jobseeker", "super_admin")),
    db: Session = Depends(get_db),
):
    profile = db.query(JobSeekerProfile).filter(JobSeekerProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Application not found")

    app = db.query(JobApplication).filter(
        JobApplication.id == application_id,
        JobApplication.jobseeker_id == profile.id,
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    return success_response(
        data={
            "id": app.id,
            "status": app.status,
            "cover_letter": app.cover_letter,
            "resume_url": app.resume_url,
            "recruiter_notes": app.recruiter_notes,
            "applied_at": app.created_at,
            "updated_at": app.updated_at,
            "job": {
                "id": app.job.id,
                "title": app.job.title,
                "job_type": app.job.job_type,
                "city": app.job.city,
                "company_name": app.job.company.company_name if app.job.company else "Unknown",
            } if app.job else None,
        }
    )
