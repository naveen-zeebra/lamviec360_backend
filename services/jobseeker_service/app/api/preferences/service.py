# ─────────────────────────────────────────────────────────────────────────────
# File    : services/jobseeker_service/app/api/preferences/service.py
# Purpose : Business logic for Job Seeker notification & language preferences
# ─────────────────────────────────────────────────────────────────────────────

from sqlalchemy.orm import Session
from shared.models.user import User
from shared.models.notification_preference import NotificationPreference
from services.jobseeker_service.app.api.preferences.schemas import (
    SeekerPreferencesResponse,
    SeekerNotificationToggles,
    UpdateSeekerPreferencesRequest,
)


def get_seeker_preferences(db: Session, user: User) -> SeekerPreferencesResponse:
    """Retrieve user language and notification preferences, creating defaults if not yet persisted."""
    pref = db.query(NotificationPreference).filter(NotificationPreference.user_id == user.id).first()
    if not pref:
        pref = NotificationPreference(
            user_id=user.id,
            email_job_recommendations=True,
            email_application_updates=True,
            email_interview_alerts=True,
            email_marketing=False,
            in_app_enabled=True,
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)

    lang = getattr(user, "preferred_language", "vi") or "vi"

    return SeekerPreferencesResponse(
        preferred_language=lang,
        notifications=SeekerNotificationToggles(
            job_recommendations=pref.email_job_recommendations,
            application_updates=pref.email_application_updates,
            interview_alerts=pref.email_interview_alerts,
            marketing=pref.email_marketing,
            in_app_enabled=pref.in_app_enabled,
        ),
    )


def update_seeker_preferences(
    db: Session, user: User, payload: UpdateSeekerPreferencesRequest
) -> SeekerPreferencesResponse:
    """Update preferred language and notification switches."""
    if payload.preferred_language is not None:
        valid_lang = payload.preferred_language.lower() if payload.preferred_language.lower() in ("vi", "en") else "vi"
        user.preferred_language = valid_lang
        db.add(user)

    pref = db.query(NotificationPreference).filter(NotificationPreference.user_id == user.id).first()
    if not pref:
        pref = NotificationPreference(user_id=user.id)
        db.add(pref)

    if payload.job_recommendations is not None:
        pref.email_job_recommendations = payload.job_recommendations
    if payload.application_updates is not None:
        pref.email_application_updates = payload.application_updates
    if payload.interview_alerts is not None:
        pref.email_interview_alerts = payload.interview_alerts
    if payload.marketing is not None:
        pref.email_marketing = payload.marketing
    if payload.in_app_enabled is not None:
        pref.in_app_enabled = payload.in_app_enabled

    db.commit()
    db.refresh(pref)
    db.refresh(user)

    return get_seeker_preferences(db, user)

