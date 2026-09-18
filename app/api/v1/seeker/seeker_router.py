from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_seeker
from app.models.user import User
from app.models.seeker import SeekerProfile, SeekerResume, SavedJob
from app.models.job import Job
from app.models.application import Application, ApplicationTimeline
from app.models.interview import Interview
from app.models.notification import Notification
from app.models.enums import ApplicationStage, InterviewStatus, NotificationType, JobStatus
from app.schemas.seeker import SeekerProfileUpdate, ResumeUploadRequest, SeekerProfileOut
from app.schemas.application import ApplicationApplyRequest
from app.schemas.interview import InterviewRespondRequest, InterviewOut
from app.schemas.job import JobOut
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/seeker", tags=["Job Seeker Workspace"])


def compute_completeness(profile: SeekerProfile, user: User) -> int:
    checks = [
        bool(user.name),
        bool(profile.phone),
        bool(profile.location),
        bool(profile.title),
        bool(profile.industry),
        bool(profile.skills and len(profile.skills) > 0),
        bool(profile.education and len(profile.education) > 0),
        bool(profile.experience and len(profile.experience) > 0),
        bool(profile.resume_file_name),
        bool(profile.preferences and len(profile.preferences.get("roles", [])) > 0),
    ]
    done = sum(1 for c in checks if c)
    return round((done / len(checks)) * 100)


@router.get("/profile", response_model=SeekerProfileOut)
def get_seeker_profile(current_user: User = Depends(get_current_seeker), db: Session = Depends(get_db)):
    """Retrieves full profile details for the authenticated Job Seeker."""
    p = current_user.seeker_profile
    if not p:
        p = SeekerProfile(user_id=current_user.id)
        db.add(p)
        db.commit()
        db.refresh(p)

    return SeekerProfileOut(
        user_id=current_user.id,
        personal={
            "fullName": current_user.name,
            "phone": p.phone or "",
            "location": p.location or "",
            "photo": p.photo_data_url or "",
        },
        professional={"title": p.title or "", "experience": p.experience_years or "", "industry": p.industry or "", "skills": p.skills or []},
        languages=p.languages or [],
        education=p.education or [],
        experience=p.experience or [],
        resume={
            "fileName": p.resume_file_name or "",
            "size": p.resume_size or 0,
            "mimeType": p.resume_mime_type or "",
            "uploadedAt": p.resume_uploaded_at.strftime("%Y-%m-%d") if p.resume_uploaded_at else "",
            # base64 data is fetched separately via GET /seeker/resume/download to keep profile response lightweight
            "dataUrl": "",
        },
        preferences=p.preferences or {"roles": [], "locations": [], "workMode": "", "salary": ""},
        completeness=compute_completeness(p, current_user),
    )


@router.put("/profile", response_model=SeekerProfileOut)
def update_seeker_profile(req: SeekerProfileUpdate, current_user: User = Depends(get_current_seeker), db: Session = Depends(get_db)):
    """Updates seeker profile personal, professional, education, experience, or preference records."""
    p = current_user.seeker_profile
    if not p:
        p = SeekerProfile(user_id=current_user.id)
        db.add(p)

    if req.personal:
        if "fullName" in req.personal and req.personal["fullName"]:
            current_user.name = req.personal["fullName"]
        if "phone" in req.personal:
            p.phone = req.personal["phone"]
        if "location" in req.personal:
            p.location = req.personal["location"]
        # Profile photo stored as base64 data-URL
        if "photo" in req.personal and req.personal["photo"]:
            data_url = req.personal["photo"]
            # extract mime type from "data:<mime>;base64,..."
            mime = "image/jpeg"
            if data_url.startswith("data:"):
                try:
                    mime = data_url.split(";")[0].split(":")[1]
                except Exception:
                    pass
            p.photo_data_url = data_url
            p.photo_mime_type = mime

    if req.professional:
        if "title" in req.professional:
            p.title = req.professional["title"]
        if "experience" in req.professional:
            p.experience_years = req.professional["experience"]
        if "industry" in req.professional:
            p.industry = req.professional["industry"]
        if "skills" in req.professional:
            p.skills = req.professional["skills"]

    if req.languages is not None:
        p.languages = req.languages
    if req.education is not None:
        p.education = req.education
    if req.experience is not None:
        p.experience = req.experience
    if req.preferences is not None:
        p.preferences = req.preferences
    if req.privacy is not None:
        p.privacy_settings = req.privacy

    db.commit()
    return get_seeker_profile(current_user=current_user, db=db)


@router.post("/resume", response_model=MessageResponse)
def save_seeker_resume(req: ResumeUploadRequest, current_user: User = Depends(get_current_seeker), db: Session = Depends(get_db)):
    """Stores resume metadata in seeker_profiles and base64 blob in seeker_resumes table."""
    p = current_user.seeker_profile
    if not p:
        p = SeekerProfile(user_id=current_user.id)
        db.add(p)
        db.flush()

    # Extract mime type from data-URL prefix
    mime = req.mime_type or "application/octet-stream"
    if req.data_url and req.data_url.startswith("data:"):
        try:
            mime = req.data_url.split(";")[0].split(":")[1]
        except Exception:
            pass

    # Update metadata in profile
    p.resume_file_name = req.file_name
    p.resume_size = req.size
    p.resume_mime_type = mime
    p.resume_uploaded_at = datetime.utcnow()

    # Upsert binary blob in separate table
    if req.data_url:
        blob = db.query(SeekerResume).filter(SeekerResume.user_id == current_user.id).first()
        if blob:
            blob.base64_data = req.data_url
            blob.updated_at = datetime.utcnow()
        else:
            blob = SeekerResume(user_id=current_user.id, base64_data=req.data_url)
            db.add(blob)

    db.commit()
    return MessageResponse(success=True, message="Resume saved successfully.")


@router.get("/resume/download", response_model=MessageResponse)
def download_seeker_resume(current_user: User = Depends(get_current_seeker), db: Session = Depends(get_db)):
    """Returns the base64 resume blob for the authenticated seeker."""
    blob = db.query(SeekerResume).filter(SeekerResume.user_id == current_user.id).first()
    if not blob or not blob.base64_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No resume uploaded yet.")
    p = current_user.seeker_profile
    return MessageResponse(
        success=True,
        message="Resume data retrieved.",
        data={
            "fileName": p.resume_file_name if p else "",
            "mimeType": p.resume_mime_type if p else "",
            "size": p.resume_size if p else 0,
            "dataUrl": blob.base64_data,
        },
    )


@router.delete("/resume", response_model=MessageResponse)
def remove_seeker_resume(current_user: User = Depends(get_current_seeker), db: Session = Depends(get_db)):
    """Deletes the seeker's current resume metadata and binary blob."""
    p = current_user.seeker_profile
    if p:
        p.resume_file_name = ""
        p.resume_size = 0
        p.resume_mime_type = ""
        p.resume_uploaded_at = None
    blob = db.query(SeekerResume).filter(SeekerResume.user_id == current_user.id).first()
    if blob:
        db.delete(blob)
    db.commit()
    return MessageResponse(success=True, message="Resume removed.")


@router.get("/applications")
def list_seeker_applications(current_user: User = Depends(get_current_seeker), db: Session = Depends(get_db)):
    """Lists all job applications submitted by the seeker."""
    apps = db.query(Application).filter(Application.seeker_id == current_user.id).order_by(Application.applied_date.desc()).all()
    results = []
    for a in apps:
        j = a.job
        timeline_list = [{"stage": t.stage.value, "date": t.created_at.strftime("%Y-%m-%d")} for t in a.timeline]
        interview_data = None
        if a.interview:
            interview_data = {
                "id": a.interview.id,
                "status": a.interview.status.value,
                "at": a.interview.scheduled_at.strftime("%Y-%m-%d %H:%M"),
                "durationMin": a.interview.duration_min,
                "mode": a.interview.mode.value,
                "location": a.interview.location_or_link,
                "round": a.interview.round_name,
                "interviewers": a.interview.interviewers or [],
                "instructions": a.interview.instructions or "",
                "documents": a.interview.documents or [],
            }

        results.append(
            {
                "id": a.id,
                "jobId": a.job_id,
                "jobTitle": j.title if j else "",
                "company": j.company.name if j and j.company else "",
                "companyLogo": j.company.logo if j and j.company else "",
                "appliedDate": a.applied_date.strftime("%Y-%m-%d"),
                "stage": a.stage.value,
                "closed": a.closed,
                "timeline": timeline_list,
                "resumeFileName": a.resume_file_name or "",
                "coverLetter": a.cover_letter or "",
                "interview": interview_data,
            }
        )
    return results


@router.post("/jobs/{id}/apply", response_model=MessageResponse)
def apply_to_job(id: str, req: ApplicationApplyRequest, current_user: User = Depends(get_current_seeker), db: Session = Depends(get_db)):
    """Submits a job application for a specific published job."""
    job = db.query(Job).filter(Job.id == id).first()
    if not job or job.status != JobStatus.PUBLISHED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job is not open for applications.")

    # Check duplicate application
    existing = db.query(Application).filter(Application.job_id == id, Application.seeker_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You have already applied for this role.")

    profile = current_user.seeker_profile
    resume_file = req.resume_file_name or (profile.resume_file_name if profile else "")

    app = Application(
        job_id=id,
        seeker_id=current_user.id,
        stage=ApplicationStage.APPLIED,
        match_score=75,  # Baseline match score
        resume_file_name=resume_file,
        cover_letter=req.cover_letter or "",
        answers=req.answers or {},
    )
    db.add(app)
    db.flush()

    # Add initial timeline entry
    t = ApplicationTimeline(application_id=app.id, stage=ApplicationStage.APPLIED)
    db.add(t)

    # Notify employer
    if job.company:
        employer_admin = db.query(User).filter(User.company_id == job.company_id).first()
        if employer_admin:
            notif = Notification(
                recipient_id=employer_admin.id,
                type=NotificationType.APPLICATION,
                title="New application",
                message=f"{current_user.name} applied to {job.title}.",
                application_id=app.id,
            )
            db.add(notif)

    db.commit()
    return MessageResponse(success=True, message="Application submitted successfully!", data={"application_id": app.id})


@router.post("/applications/{id}/withdraw", response_model=MessageResponse)
def withdraw_application(id: str, current_user: User = Depends(get_current_seeker), db: Session = Depends(get_db)):
    """Withdraws an active application."""
    app = db.query(Application).filter(Application.id == id, Application.seeker_id == current_user.id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

    app.stage = ApplicationStage.WITHDRAWN
    app.closed = True
    t = ApplicationTimeline(application_id=app.id, stage=ApplicationStage.WITHDRAWN)
    db.add(t)
    db.commit()

    return MessageResponse(success=True, message="Application withdrawn.")


@router.get("/saved-jobs", response_model=List[JobOut])
def list_saved_jobs(current_user: User = Depends(get_current_seeker), db: Session = Depends(get_db)):
    """Returns list of jobs bookmarked by the seeker."""
    jobs = (
        db.query(Job)
        .join(SavedJob, Job.id == SavedJob.job_id)
        .filter(SavedJob.user_id == current_user.id)
        .all()
    )
    return jobs


@router.post("/saved-jobs/{id}/toggle", response_model=MessageResponse)
def toggle_saved_job(id: str, current_user: User = Depends(get_current_seeker), db: Session = Depends(get_db)):
    """Toggles saving/bookmarking a job."""
    existing = db.query(SavedJob).filter(SavedJob.user_id == current_user.id, SavedJob.job_id == id).first()
    if existing:
        db.delete(existing)
        db.commit()
        return MessageResponse(success=True, message="Job removed from saved list.", data={"saved": False})
    else:
        saved = SavedJob(user_id=current_user.id, job_id=id)
        db.add(saved)
        db.commit()
        return MessageResponse(success=True, message="Job saved.", data={"saved": True})


@router.get("/interviews", response_model=List[InterviewOut])
def list_seeker_interviews(current_user: User = Depends(get_current_seeker), db: Session = Depends(get_db)):
    """Lists upcoming or past interviews for the job seeker."""
    interviews = (
        db.query(Interview)
        .join(Application, Interview.application_id == Application.id)
        .filter(Application.seeker_id == current_user.id)
        .order_by(Interview.scheduled_at.asc())
        .all()
    )

    out = []
    for i in interviews:
        app = i.application
        job = app.job if app else None
        out.append(
            InterviewOut(
                id=i.id,
                application_id=i.application_id,
                job_id=app.job_id if app else "",
                job_title=job.title if job else "",
                company_name=job.company.name if job and job.company else "",
                round_name=i.round_name,
                scheduled_at=i.scheduled_at.strftime("%Y-%m-%d %H:%M"),
                duration_min=i.duration_min,
                mode=i.mode.value,
                location_or_link=i.location_or_link or "",
                instructions=i.instructions or "",
                interviewers=i.interviewers or [],
                documents=i.documents or [],
                status=i.status.value,
                response_note=i.response_note,
                response_at=i.response_at.strftime("%Y-%m-%d") if i.response_at else None,
            )
        )
    return out


@router.post("/interviews/{id}/respond", response_model=MessageResponse)
def respond_interview(id: str, req: InterviewRespondRequest, current_user: User = Depends(get_current_seeker), db: Session = Depends(get_db)):
    """Allows seeker to confirm or decline an interview invitation."""
    interview = (
        db.query(Interview)
        .join(Application, Interview.application_id == Application.id)
        .filter(Interview.id == id, Application.seeker_id == current_user.id)
        .first()
    )
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found.")

    if req.status == "confirmed":
        interview.status = InterviewStatus.CONFIRMED
    else:
        interview.status = InterviewStatus.DECLINED

    interview.response_note = req.note or ""
    interview.response_at = datetime.utcnow()
    db.commit()

    return MessageResponse(success=True, message=f"Interview {req.status}.")


@router.get("/notifications")
def get_seeker_notifications(current_user: User = Depends(get_current_seeker), db: Session = Depends(get_db)):
    """Retrieves notifications for seeker."""
    notifs = db.query(Notification).filter(Notification.recipient_id == current_user.id).order_by(Notification.created_at.desc()).all()
    return [
        {
            "id": n.id,
            "type": n.type.value,
            "title": n.title,
            "message": n.message,
            "date": n.created_at.strftime("%Y-%m-%d"),
            "read": n.read,
            "applicationId": n.application_id,
        }
        for n in notifs
    ]


@router.patch("/notifications/{id}/read", response_model=MessageResponse)
def mark_seeker_notification_read(id: str, current_user: User = Depends(get_current_seeker), db: Session = Depends(get_db)):
    n = db.query(Notification).filter(Notification.id == id, Notification.recipient_id == current_user.id).first()
    if n:
        n.read = True
        db.commit()
    return MessageResponse(success=True, message="Marked as read.")
