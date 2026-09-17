import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_company_user, get_current_company_admin
from app.models.user import User
from app.models.company import Company, CompanyInvitation
from app.models.job import Job
from app.models.application import Application, ApplicationNote, ApplicationTimeline
from app.models.interview import Interview
from app.models.notification import Notification
from app.models.plan import SubscriptionPlan
from app.models.enums import (
    UserRole,
    UserStatus,
    JobStatus,
    ApplicationStage,
    InterviewMode,
    InterviewStatus,
    NotificationType,
)
from app.schemas.company import (
    CompanyOut,
    CompanyUpdate,
    QuotaOut,
    TeamMemberOut,
    InviteMemberRequest,
    InvitationOut,
)
from app.schemas.job import JobCreate, JobUpdate, JobOut
from app.schemas.application import (
    CandidateOut,
    ApplicationStageUpdate,
    BulkStageUpdateRequest,
    AddNoteRequest,
    NoteOut,
)
from app.schemas.interview import InterviewCreateRequest
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/company", tags=["Company Workspace"])

PLAN_LIMITS = {
    "Freemium": 3,
    "Professional": 25,
    "Enterprise": None,  # Unlimited
}


def calculate_quota(company: Company, db: Session) -> QuotaOut:
    plan_id = company.plan_id or "Freemium"
    limit = PLAN_LIMITS.get(plan_id, 3)
    active_count = (
        db.query(Job)
        .filter(Job.company_id == company.id, Job.status.in_([JobStatus.PUBLISHED, JobStatus.PAUSED]))
        .count()
    )
    remaining = (limit - active_count) if limit is not None else None
    if remaining is not None and remaining < 0:
        remaining = 0
    return QuotaOut(plan=plan_id, limit=limit, used=active_count, remaining=remaining)


@router.get("/profile", response_model=CompanyOut)
def get_company_profile(current_user: User = Depends(get_current_company_user), db: Session = Depends(get_db)):
    """Fetches company profile, verification state, subscription plan, and job quota."""
    c = current_user.company
    quota = calculate_quota(c, db)
    return CompanyOut(
        id=c.id,
        name=c.name,
        reg_number=c.reg_number,
        industry=c.industry,
        size=c.size,
        website=c.website,
        description=c.description,
        logo=c.logo,
        verified=c.verified,
        email_verified=c.email_verified,
        approval_status=c.approval_status.value,
        plan=c.plan_id,
        quota=quota,
        settings=c.settings or {},
    )


@router.put("/profile", response_model=CompanyOut)
def update_company_profile(
    req: CompanyUpdate,
    current_user: User = Depends(get_current_company_admin),
    db: Session = Depends(get_db),
):
    """Updates company profile details (Company Admin only)."""
    c = current_user.company
    for key, value in req.model_dump(exclude_unset=True).items():
        setattr(c, key, value)
    db.commit()
    return get_company_profile(current_user=current_user, db=db)


@router.get("/dashboard")
def get_company_dashboard(current_user: User = Depends(get_current_company_user), db: Session = Depends(get_db)):
    """Computes roll-up metrics for company dashboard overview."""
    c = current_user.company
    active_jobs = db.query(Job).filter(Job.company_id == c.id, Job.status == JobStatus.PUBLISHED).count()
    quota = calculate_quota(c, db)

    total_apps = (
        db.query(Application)
        .join(Job, Application.job_id == Job.id)
        .filter(Job.company_id == c.id)
        .count()
    )

    interviews_this_week = (
        db.query(Interview)
        .join(Application, Interview.application_id == Application.id)
        .join(Job, Application.job_id == Job.id)
        .filter(
            Job.company_id == c.id,
            Interview.scheduled_at >= datetime.utcnow(),
            Interview.scheduled_at <= datetime.utcnow() + timedelta(days=7),
        )
        .count()
    )

    filled_mtd = (
        db.query(Application)
        .join(Job, Application.job_id == Job.id)
        .filter(Job.company_id == c.id, Application.stage == ApplicationStage.HIRED)
        .count()
    )

    return {
        "activeJobs": active_jobs,
        "quota": quota.model_dump(),
        "applications": total_apps,
        "interviewsThisWeek": interviews_this_week,
        "filledMtd": filled_mtd,
        "plan": {"id": c.plan_id, "name": c.plan_id},
    }


# ---- JOBS MANAGEMENT ----


@router.get("/jobs", response_model=List[JobOut])
def list_company_jobs(current_user: User = Depends(get_current_company_user), db: Session = Depends(get_db)):
    """Lists all jobs created by this company with application counts."""
    jobs = db.query(Job).filter(Job.company_id == current_user.company_id).order_by(Job.created_at.desc()).all()
    out = []
    for j in jobs:
        out.append(
            JobOut(
                id=j.id,
                company_id=j.company_id,
                company_name=current_user.company.name,
                company_logo=current_user.company.logo or "",
                title=j.title,
                department=j.department,
                type=j.type,
                location=j.location,
                salary_min=j.salary_min,
                salary_max=j.salary_max,
                negotiable=j.negotiable,
                jd=j.jd,
                skills=j.skills or [],
                experience=j.experience,
                education=j.education,
                deadline=j.deadline.strftime("%Y-%m-%d") if j.deadline else None,
                vacancies=j.vacancies,
                documents=j.documents or [],
                status=j.status.value,
                ai_generated=j.ai_generated,
                created_at=j.created_at.strftime("%Y-%m-%d"),
                applicant_count=len(j.applications) if j.applications else 0,
            )
        )
    return out


@router.post("/jobs", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_company_job(req: JobCreate, current_user: User = Depends(get_current_company_user), db: Session = Depends(get_db)):
    """Creates a new job posting for this company with plan quota verification."""
    c = current_user.company
    quota = calculate_quota(c, db)

    # Check quota if creating as Published
    if req.status == "Published" and quota.remaining is not None and quota.remaining <= 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You have reached your {quota.plan} plan limit of {quota.limit} active job postings. Please upgrade to post more.",
        )

    job_status = JobStatus.PUBLISHED if req.status == "Published" else JobStatus.DRAFT

    job = Job(
        company_id=c.id,
        creator_id=current_user.id,
        title=req.title,
        department=req.department or "",
        type=req.type,
        location=req.location,
        salary_min=req.salary_min,
        salary_max=req.salary_max,
        negotiable=req.negotiable,
        jd=req.jd,
        skills=req.skills,
        experience=req.experience or "",
        education=req.education or "",
        deadline=req.deadline,
        vacancies=req.vacancies,
        documents=req.documents,
        status=job_status,
        ai_generated=req.ai_generated,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return JobOut(
        id=job.id,
        company_id=job.company_id,
        company_name=c.name,
        company_logo=c.logo or "",
        title=job.title,
        department=job.department,
        type=job.type,
        location=job.location,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        negotiable=job.negotiable,
        jd=job.jd,
        skills=job.skills or [],
        experience=job.experience,
        education=job.education,
        deadline=job.deadline.strftime("%Y-%m-%d") if job.deadline else None,
        vacancies=job.vacancies,
        documents=job.documents or [],
        status=job.status.value,
        ai_generated=job.ai_generated,
        created_at=job.created_at.strftime("%Y-%m-%d"),
        applicant_count=0,
    )


@router.get("/jobs/{id}", response_model=JobOut)
def get_company_job(id: str, current_user: User = Depends(get_current_company_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == id, Job.company_id == current_user.company_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return JobOut(
        id=job.id,
        company_id=job.company_id,
        company_name=current_user.company.name,
        company_logo=current_user.company.logo or "",
        title=job.title,
        department=job.department,
        type=job.type,
        location=job.location,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        negotiable=job.negotiable,
        jd=job.jd,
        skills=job.skills or [],
        experience=job.experience,
        education=job.education,
        deadline=job.deadline.strftime("%Y-%m-%d") if job.deadline else None,
        vacancies=job.vacancies,
        documents=job.documents or [],
        status=job.status.value,
        ai_generated=job.ai_generated,
        created_at=job.created_at.strftime("%Y-%m-%d"),
        applicant_count=len(job.applications) if job.applications else 0,
    )


@router.put("/jobs/{id}", response_model=JobOut)
def update_company_job(id: str, req: JobUpdate, current_user: User = Depends(get_current_company_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == id, Job.company_id == current_user.company_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    for key, val in req.model_dump(exclude_unset=True).items():
        if key == "status" and val:
            setattr(job, "status", JobStatus(val))
        else:
            setattr(job, key, val)

    db.commit()
    db.refresh(job)
    return get_company_job(id=id, current_user=current_user, db=db)


@router.patch("/jobs/{id}/status", response_model=MessageResponse)
def set_job_status(id: str, status_val: str = Query(..., alias="status"), current_user: User = Depends(get_current_company_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == id, Job.company_id == current_user.company_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if status_val == "Published":
        quota = calculate_quota(current_user.company, db)
        if quota.remaining is not None and quota.remaining <= 0 and job.status != JobStatus.PUBLISHED:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Quota exceeded. Upgrade plan to publish.")

    job.status = JobStatus(status_val)
    db.commit()
    return MessageResponse(success=True, message=f"Job status updated to {status_val}")


@router.post("/jobs/{id}/duplicate", response_model=JobOut)
def duplicate_company_job(id: str, current_user: User = Depends(get_current_company_user), db: Session = Depends(get_db)):
    src = db.query(Job).filter(Job.id == id, Job.company_id == current_user.company_id).first()
    if not src:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    copy_job = Job(
        company_id=src.company_id,
        creator_id=current_user.id,
        title=f"{src.title} (Copy)",
        department=src.department,
        type=src.type,
        location=src.location,
        salary_min=src.salary_min,
        salary_max=src.salary_max,
        negotiable=src.negotiable,
        jd=src.jd,
        skills=src.skills,
        experience=src.experience,
        education=src.education,
        deadline=None,
        vacancies=src.vacancies,
        documents=src.documents,
        status=JobStatus.DRAFT,
        ai_generated=False,
    )
    db.add(copy_job)
    db.commit()
    db.refresh(copy_job)
    return get_company_job(id=copy_job.id, current_user=current_user, db=db)


# ---- CANDIDATE PIPELINE ----


@router.get("/candidates", response_model=List[CandidateOut])
def list_candidates(
    job_id: Optional[str] = None,
    stage: Optional[str] = None,
    current_user: User = Depends(get_current_company_user),
    db: Session = Depends(get_db),
):
    """Lists candidates who applied for company jobs, optionally filtered by job or stage."""
    query = (
        db.query(Application)
        .join(Job, Application.job_id == Job.id)
        .filter(Job.company_id == current_user.company_id)
    )

    if job_id:
        query = query.filter(Application.job_id == job_id)
    if stage:
        query = query.filter(Application.stage == ApplicationStage(stage))

    apps = query.order_by(Application.applied_date.desc()).all()
    results = []
    for a in apps:
        seeker = a.seeker
        profile = seeker.seeker_profile if seeker else None
        job = a.job

        notes_out = [
            NoteOut(id=n.id, text=n.text, author=n.author, at=n.created_at.strftime("%Y-%m-%d"))
            for n in a.notes
        ]

        interview_dict = None
        if a.interview:
            interview_dict = {
                "id": a.interview.id,
                "round": a.interview.round_name,
                "at": a.interview.scheduled_at.strftime("%Y-%m-%d %H:%M"),
                "status": a.interview.status.value,
                "mode": a.interview.mode.value,
                "location": a.interview.location_or_link,
            }

        results.append(
            CandidateOut(
                id=a.id,
                job_id=a.job_id,
                job_title=job.title if job else "",
                name=seeker.name if seeker else "Unknown",
                email=seeker.email if seeker else "",
                phone=profile.phone if profile else "",
                experience_years=int(profile.experience_years) if profile and profile.experience_years and profile.experience_years.isdigit() else 2,
                education_level=profile.education[0].get("degree", "Bachelor's Degree") if profile and profile.education else "Bachelor's Degree",
                applied_date=a.applied_date.strftime("%Y-%m-%d"),
                stage=a.stage.value,
                match_score=a.match_score,
                resume_file_name=a.resume_file_name or (profile.resume_file_name if profile else ""),
                notes=notes_out,
                interview=interview_dict,
                rejection_template_id=a.rejection_template_id,
                rejection_note=a.rejection_note,
                rejected_at=a.rejected_at.strftime("%Y-%m-%d") if a.rejected_at else None,
            )
        )
    return results


@router.patch("/candidates/{id}/stage", response_model=MessageResponse)
def update_candidate_stage(
    id: str,
    req: ApplicationStageUpdate,
    current_user: User = Depends(get_current_company_user),
    db: Session = Depends(get_db),
):
    """Moves candidate across pipeline stages."""
    app = (
        db.query(Application)
        .join(Job, Application.job_id == Job.id)
        .filter(Application.id == id, Job.company_id == current_user.company_id)
        .first()
    )
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate record not found")

    new_stage = ApplicationStage(req.stage)
    app.stage = new_stage

    if new_stage == ApplicationStage.REJECTED:
        app.rejection_template_id = req.rejection_template_id
        app.rejection_note = req.rejection_note
        app.rejected_at = datetime.utcnow()

    # Timeline entry
    timeline = ApplicationTimeline(application_id=app.id, stage=new_stage)
    db.add(timeline)

    # Candidate notification
    notif = Notification(
        recipient_id=app.seeker_id,
        type=NotificationType.STATUS,
        title=f"Application update: {new_stage.value}",
        message=f"Your application status for {app.job.title} changed to {new_stage.value}.",
        application_id=app.id,
    )
    db.add(notif)
    db.commit()

    return MessageResponse(success=True, message=f"Candidate stage updated to {req.stage}")


@router.post("/candidates/bulk-stage", response_model=MessageResponse)
def bulk_update_candidate_stage(
    req: BulkStageUpdateRequest,
    current_user: User = Depends(get_current_company_user),
    db: Session = Depends(get_db),
):
    """Bulk updates candidate stages."""
    new_stage = ApplicationStage(req.stage)
    apps = (
        db.query(Application)
        .join(Job, Application.job_id == Job.id)
        .filter(Application.id.in_(req.application_ids), Job.company_id == current_user.company_id)
        .all()
    )

    for a in apps:
        a.stage = new_stage
        if new_stage == ApplicationStage.REJECTED:
            a.rejection_template_id = req.rejection_template_id
            a.rejection_note = req.rejection_note
            a.rejected_at = datetime.utcnow()
        t = ApplicationTimeline(application_id=a.id, stage=new_stage)
        db.add(t)

    db.commit()
    return MessageResponse(success=True, message=f"Updated {len(apps)} candidates to {req.stage}")


@router.post("/candidates/{id}/notes", response_model=MessageResponse)
def add_candidate_note(
    id: str,
    req: AddNoteRequest,
    current_user: User = Depends(get_current_company_user),
    db: Session = Depends(get_db),
):
    """Adds internal evaluation note to candidate."""
    app = (
        db.query(Application)
        .join(Job, Application.job_id == Job.id)
        .filter(Application.id == id, Job.company_id == current_user.company_id)
        .first()
    )
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate record not found")

    note = ApplicationNote(
        application_id=app.id,
        author=current_user.name,
        text=req.text,
    )
    db.add(note)
    db.commit()
    return MessageResponse(success=True, message="Note added.")


@router.post("/candidates/{id}/schedule-interview", response_model=MessageResponse)
def schedule_candidate_interview(
    id: str,
    req: InterviewCreateRequest,
    current_user: User = Depends(get_current_company_user),
    db: Session = Depends(get_db),
):
    """Schedules an interview round and dispatches notification to candidate."""
    app = (
        db.query(Application)
        .join(Job, Application.job_id == Job.id)
        .filter(Application.id == id, Job.company_id == current_user.company_id)
        .first()
    )
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    # If interview already exists, update it, else create new
    if app.interview:
        app.interview.round_name = req.round_name
        app.interview.scheduled_at = req.scheduled_at
        app.interview.duration_min = req.duration_min
        app.interview.mode = InterviewMode(req.mode)
        app.interview.location_or_link = req.location_or_link
        app.interview.instructions = req.instructions or ""
        app.interview.interviewers = req.interviewers
        app.interview.documents = req.documents
        app.interview.status = InterviewStatus.INVITED
    else:
        interview = Interview(
            application_id=app.id,
            round_name=req.round_name,
            scheduled_at=req.scheduled_at,
            duration_min=req.duration_min,
            mode=InterviewMode(req.mode),
            location_or_link=req.location_or_link,
            instructions=req.instructions or "",
            interviewers=req.interviewers,
            documents=req.documents,
            status=InterviewStatus.INVITED,
        )
        db.add(interview)

    app.stage = ApplicationStage.INTERVIEW_SCHEDULED
    t = ApplicationTimeline(application_id=app.id, stage=ApplicationStage.INTERVIEW_SCHEDULED)
    db.add(t)

    # Notify seeker
    notif = Notification(
        recipient_id=app.seeker_id,
        type=NotificationType.INTERVIEW,
        title="Interview Scheduled",
        message=f"An interview for {app.job.title} has been scheduled on {req.scheduled_at.strftime('%Y-%m-%d %H:%M')}.",
        application_id=app.id,
    )
    db.add(notif)
    db.commit()

    return MessageResponse(success=True, message="Interview scheduled and invitation dispatched.")


# ---- TEAM MANAGEMENT ----


@router.get("/team", response_model=Dict[str, Any])
def get_company_team(current_user: User = Depends(get_current_company_user), db: Session = Depends(get_db)):
    """Lists company team members and pending invitations."""
    members = db.query(User).filter(User.company_id == current_user.company_id).all()
    invites = db.query(CompanyInvitation).filter(CompanyInvitation.company_id == current_user.company_id).all()

    members_out = [
        TeamMemberOut(
            id=m.id,
            name=m.name,
            email=m.email,
            role=m.role.value,
            status=m.status.value,
            created_at=m.created_at,
            last_login=m.last_login_at.strftime("%Y-%m-%d") if m.last_login_at else "Never",
        )
        for m in members
    ]

    invites_out = [
        InvitationOut(
            id=i.id,
            email=i.email,
            role=i.role.value,
            message=i.message or "",
            status=i.status,
            sent_date=i.sent_date,
            expiry=i.expiry,
        )
        for i in invites
    ]

    return {"members": members_out, "invitations": invites_out}


@router.post("/team/invite", response_model=MessageResponse)
def invite_team_member(
    req: InviteMemberRequest,
    current_user: User = Depends(get_current_company_admin),
    db: Session = Depends(get_db),
):
    """Invites a recruiter or viewer to the company workspace."""
    existing_user = db.query(User).filter(User.email == req.email.lower()).first()
    if existing_user and existing_user.company_id == current_user.company_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This user is already part of your team.")

    invite_token = f"inv_{uuid.uuid4().hex}"
    assigned_role = UserRole.COMPANY_HR if req.role == "HR / Recruiter" else UserRole.COMPANY_VIEWER

    invitation = CompanyInvitation(
        company_id=current_user.company_id,
        email=req.email.lower(),
        role=assigned_role,
        invite_token=invite_token,
        message=req.message or "",
        status="Pending",
        sent_date=datetime.utcnow(),
        expiry=datetime.utcnow() + timedelta(days=7),
    )
    db.add(invitation)
    db.commit()

    return MessageResponse(
        success=True,
        message=f"Invitation sent to {req.email}.",
        data={"invite_token": invite_token},
    )


@router.delete("/team/invites/{id}", response_model=MessageResponse)
def revoke_invitation(id: str, current_user: User = Depends(get_current_company_admin), db: Session = Depends(get_db)):
    inv = db.query(CompanyInvitation).filter(CompanyInvitation.id == id, CompanyInvitation.company_id == current_user.company_id).first()
    if inv:
        inv.status = "Revoked"
        db.commit()
    return MessageResponse(success=True, message="Invitation revoked.")


@router.post("/data-retention/purge", response_model=MessageResponse)
def purge_company_data(months: int = Query(6, ge=1, le=36), current_user: User = Depends(get_current_company_admin), db: Session = Depends(get_db)):
    """Purges rejected candidate records older than specified months for compliance and GDPR/data retention."""
    cutoff = datetime.utcnow() - timedelta(days=months * 30)
    purged_count = (
        db.query(Application)
        .join(Job, Application.job_id == Job.id)
        .filter(
            Job.company_id == current_user.company_id,
            Application.stage == ApplicationStage.REJECTED,
            Application.applied_date <= cutoff,
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    return MessageResponse(success=True, message=f"Purged {purged_count} candidate records older than {months} months.")
