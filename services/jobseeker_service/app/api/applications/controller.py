# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/applications/controller.py
# Purpose : Orchestration layer for Candidate Job Applications
# ─────────────────────────────────────────────────────────────────────────────

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session

from shared.models import User
from shared.utils import log_audit_event, send_application_confirmation_email
from shared.utils.logger import get_logger

from . import service
from .schemas import JobApplicationCreateRequest

logger = get_logger("jobseeker_applications_controller")


def apply_for_job_controller(
    data: JobApplicationCreateRequest,
    user: User,
    request: Request,
    db: Session,
    upload_file=None,
    background_tasks: Optional[BackgroundTasks] = None,
) -> Dict[str, Any]:
    """Validate vacancy, apply, increment count, send 24h auto-acknowledgment email (BR-301-11), and audit event."""
    profile = service.get_or_create_profile(db, user)

    # BR-101-02: Profile Completeness (at least 60% required to apply)
    from services.jobseeker_service.app.api.profile.service import compute_profile_completeness
    completeness = compute_profile_completeness(user, profile)
    if completeness < 60:
        raise HTTPException(
            status_code=400,
            detail=f"Profile completeness must be at least 60% to apply for a job . Your profile is currently at {completeness}%. Please update your profile first.",
        )

    job = service.get_active_job(db, data.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job posting is no longer active or does not exist")

    if service.check_existing_application(db, data.job_id, profile.id):
        raise HTTPException(status_code=400, detail="You have already applied for this position")

    save_to_profile = True if data.save_to_profile is None else bool(data.save_to_profile)
    app, resume_id = service.create_application(
        db=db,
        job=job,
        profile=profile,
        cover_letter=data.cover_letter,
        resume_url=data.resume_url,
        resume_id=data.resume_id,
        upload_file=upload_file,
        save_to_profile=save_to_profile,
        resume_name=data.resume_name,
        consent=True if data.consent is None else bool(data.consent),
    )

    company_name = job.company.company_name if job.company else "Company"

    # BR-301-11: Dispatch auto-acknowledgment confirmation email to talent
    email_dispatched = False
    try:
        if background_tasks:
            background_tasks.add_task(
                send_application_confirmation_email,
                to_email=user.email,
                candidate_name=user.full_name,
                job_title=job.title,
                company_name=company_name,
                application_id=app.id,
                applied_at=app.created_at,
                job_location=job.city,
                resume_name=app.resume_name,
            )
            email_dispatched = True
        else:
            email_dispatched = send_application_confirmation_email(
                to_email=user.email,
                candidate_name=user.full_name,
                job_title=job.title,
                company_name=company_name,
                application_id=app.id,
                applied_at=app.created_at,
                job_location=job.city,
                resume_name=app.resume_name,
            )
    except Exception as email_err:
        logger.warning(f"Could not dispatch application confirmation email for app id={app.id}: {email_err}")

    # Record acknowledgment status in DB
    try:
        app.acknowledgment_sent = True
        app.acknowledgment_sent_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as db_err:
        logger.warning(f"Could not update acknowledgment status for app id={app.id}: {db_err}")

    # In-app notification
    try:
        from shared.models.notification import Notification
        notif = Notification(
            user_id=user.id,
            title="Application submitted",
            message=f"Your application for {job.title} was received. Auto-acknowledgment is processed within 24 hours (BR-301-11).",
            type="confirmation",
            application_id=app.id,
            read=False,
        )
        db.add(notif)
        db.commit()
    except Exception as notif_err:
        logger.warning(f"Could not create notification for application: {notif_err}")

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

    return {
        "application_id": app.id,
        "job_id": job.id,
        "job_title": job.title,
        "status": app.status,
        "applied_at": app.created_at.isoformat() if app.created_at else None,
        "resume_url": app.resume_url,
        "resume_id": resume_id,
        "acknowledgment_email_sent": True,
        "auto_acknowledgment_status": "dispatched" if email_dispatched else "queued",
        "acknowledgment_sla": "24_hours",
    }



def get_my_applications_controller(user: User, db: Session) -> List[Dict[str, Any]]:
    """Retrieve applicant's application history."""
    profile = service.get_or_create_profile(db, user)
    return service.list_my_applications(db, profile.id)


def get_application_detail_controller(application_id: int, user: User, db: Session) -> Dict[str, Any]:
    """Retrieve single application detail."""
    profile = service.get_or_create_profile(db, user)
    detail = service.get_application_by_id(db, application_id, profile.id)
    if not detail:
        raise HTTPException(status_code=404, detail="Application not found")
    return detail


def withdraw_application_controller(
    application_id: int,
    user: User,
    request: Request,
    db: Session,
) -> Dict[str, Any]:
    """Candidate withdraws an application before screening (BR-301-04)."""
    profile = service.get_or_create_profile(db, user)
    app = service.withdraw_application(db, application_id, profile.id)

    # In-app notification
    job_title = app.job.title if app.job else "job vacancy"
    try:
        from shared.models.notification import Notification
        notif = Notification(
            user_id=user.id,
            title="Application Withdrawn",
            message=f"You have withdrawn your application for '{job_title}'.",
            type="application",
            application_id=app.id,
            read=False,
        )
        db.add(notif)
        db.commit()
    except Exception as notif_err:
        logger.warning(f"Could not create notification for withdrawn application: {notif_err}")

    # Audit log
    log_audit_event(
        db,
        action="WITHDRAW",
        module="JOB_APPLICATIONS",
        description=f"User {user.email} withdrew application {app.id} for job '{job_title}'",
        user_id=user.id,
        user_email=user.email,
        user_type=user.user_type,
        request=request,
    )

    return {
        "application_id": app.id,
        "job_id": app.job_id,
        "job_title": job_title,
        "status": app.status,
        "withdrawn_at": app.updated_at.isoformat() if app.updated_at else None,
        "message": "Application withdrawn successfully",
    }

