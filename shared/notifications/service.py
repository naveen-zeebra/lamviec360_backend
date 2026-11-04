# ─────────────────────────────────────────────────────────────────────────────
# File    : shared/notifications/service.py
# Purpose : Cross-cutting Notification Service per LV360-FSD-006
# ─────────────────────────────────────────────────────────────────────────────

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from shared.notifications.renderer import render_notification
from shared.utils.email import send_email
from shared.utils.logger import get_logger
from shared.models.notification import Notification
from shared.models.user import User

logger = get_logger("notification_service")


class NotificationService:
    """
    Unified Notification Service orchestrating Email & In-App delivery,
    template rendering, per-stage suppression, and multilingual routing.
    """

    @classmethod
    def dispatch(
        cls,
        event: str,
        recipient_email: str,
        context: Dict[str, Any],
        db: Optional[Session] = None,
        user_id: Optional[int] = None,
        channels: Optional[List[str]] = None,
        language: Optional[str] = None,
        suppressed: bool = False,
        delay_hours: int = 0,
        application_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Dispatches a notification across specified channels.

        :param event: Scenario code e.g. 'SCN-APP-01', 'SCN-ATS-03', 'SCN-REJ-01'
        :param recipient_email: Recipient destination email address
        :param context: Dynamic tokens for template interpolation
        :param db: Optional SQLAlchemy DB session for database persistence
        :param user_id: Recipient User ID if registered
        :param channels: Delivery channels (default: ['email', 'in_app'])
        :param language: Language override ('vi' or 'en'); defaults to recipient's profile language
        :param suppressed: NTF-FR-006 HR suppression flag (if True, drops delivery)
        :param delay_hours: EMP-FR-025b scheduled sending delay (e.g. 24h buffer for rejection)
        :param application_id: Optional application link reference
        """
        if channels is None:
            channels = ["email", "in_app"]

        # 1. NTF-FR-006: Check per-stage suppression
        if suppressed:
            logger.info(
                f"[NTF-FR-006] Event '{event}' to {recipient_email} suppressed by HR."
            )
            return {
                "event": event,
                "status": "suppressed",
                "recipient": recipient_email,
                "reason": "Recruiter per-stage notification suppression",
            }

        # 2. NTF-FR-007: Determine language preference
        resolved_lang = "vi"
        if language:
            resolved_lang = language.lower()
        elif db and user_id:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user and hasattr(user, "preferred_language") and user.preferred_language:
                    resolved_lang = str(user.preferred_language).lower()
            except Exception as e:
                logger.warning(f"Failed to fetch user preferred language: {e}")

        # 3. Render localized notification content
        try:
            subject, html_body, text_body = render_notification(
                event=event,
                language=resolved_lang,
                context=context,
            )
        except Exception as e:
            logger.error(f"Failed to render notification '{event}': {e}")
            return {"event": event, "status": "error", "error": str(e)}

        results = {
            "event": event,
            "language": resolved_lang,
            "recipient": recipient_email,
            "channels": {},
        }

        # 4. Handle Delayed Sending (EMP-FR-025b / AC-017)
        if delay_hours > 0:
            scheduled_time = datetime.utcnow() + timedelta(hours=delay_hours)
            logger.info(
                f"[EMP-FR-025b] Notification '{event}' to {recipient_email} scheduled with {delay_hours}h delay (Send at: {scheduled_time.isoformat()})."
            )
            results["scheduled_time"] = scheduled_time.isoformat()
            results["delayed"] = True
            # When delayed, in production a background worker handles actual SMTP dispatch.
            # For immediate staging/demo, we register the schedule and acknowledge.
            return results

        # 5. Email Dispatch
        if "email" in channels and recipient_email:
            try:
                sent = send_email(
                    to_email=recipient_email,
                    subject=subject,
                    html_content=html_body,
                    text_content=text_body,
                )
                results["channels"]["email"] = "sent" if sent else "failed"
            except Exception as ex:
                logger.error(f"Email dispatch error for {recipient_email}: {ex}")
                results["channels"]["email"] = "failed"

        # 6. In-App Bell Notification Persistence (NTF-FR-003)
        if "in_app" in channels and db and user_id:
            try:
                notif = Notification(
                    user_id=user_id,
                    title=subject,
                    message=text_body[:400] if text_body else subject,
                    type=event.lower(),
                    application_id=application_id,
                    read=False,
                )
                db.add(notif)
                db.commit()
                results["channels"]["in_app"] = "stored"
            except Exception as ex:
                logger.warning(f"In-app notification storage error for user {user_id}: {ex}")
                results["channels"]["in_app"] = "failed"

        return results

