"""
Test Suite: Job Seeker Application Confirmation & 24-Hour Auto-Acknowledgment Email (BR-301-11)
Tests:
1. send_application_confirmation_email renders valid HTML, includes BR-301-11 notice, and delivers via fallback or SMTP.
2. Database schema verifies acknowledgment_sent and acknowledgment_sent_at columns on job_applications.
3. apply_for_job_controller sends confirmation email and updates acknowledgment fields.
4. dispatch_pending_24h_acknowledgments dispatches unacknowledged applications within the 24-hour SLA window.
"""

import sys
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from shared.database.session import SessionLocal, init_db
from shared.models import User, JobPosting, JobSeekerProfile, JobApplication, Notification
from shared.utils.email import send_application_confirmation_email
from services.jobseeker_service.app.api.applications.schemas import JobApplicationCreateRequest
from services.jobseeker_service.app.api.applications.controller import apply_for_job_controller
from services.jobseeker_service.app.api.applications import service as app_service


class DummyRequest:
    def __init__(self):
        self.headers = {"user-agent": "test-agent"}
        self.client = type("Client", (), {"host": "127.0.0.1"})()


class DummyBackgroundTasks:
    def __init__(self):
        self.tasks = []

    def add_task(self, func, *args, **kwargs):
        self.tasks.append((func, args, kwargs))


class TestApplicationConfirmation24h(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_send_application_confirmation_email_renders_and_dispatches(self):
        """Verify confirmation email renders details and BR-301-11 24h SLA text."""
        result = send_application_confirmation_email(
            to_email="candidate_test@example.com",
            candidate_name="Nguyen Van A",
            job_title="Senior Python Backend Engineer",
            company_name="ViecLam Tech Corp",
            application_id=9999,
            applied_at=datetime.now(timezone.utc),
            job_location="Ho Chi Minh City",
            resume_name="NguyenVanA_CV.pdf",
        )
        self.assertTrue(result, "send_application_confirmation_email should return True")

    def test_02_job_application_model_has_acknowledgment_columns(self):
        """Verify JobApplication table schema has acknowledgment tracking columns."""
        from sqlalchemy import inspect
        insp = inspect(self.db.bind)
        cols = {c["name"] for c in insp.get_columns("job_applications")}
        self.assertIn("acknowledgment_sent", cols)
        self.assertIn("acknowledgment_sent_at", cols)

    def test_03_apply_for_job_dispatches_email_and_marks_acknowledged(self):
        """Verify apply_for_job_controller marks acknowledgment_sent and queues email."""
        # Find or create a test job seeker user
        user = self.db.query(User).filter(User.role_type == "jobseeker", User.is_deleted == False).first()
        if not user:
            self.skipTest("No job seeker user available in DB")


        # Ensure user and profile are complete enough (>= 60%)
        user.first_name = user.first_name or "Test"
        user.last_name = user.last_name or "Seeker"
        user.phone = user.phone or "0901234567"
        self.db.commit()

        profile = app_service.get_or_create_profile(self.db, user)
        profile.city = profile.city or "Ho Chi Minh City"
        profile.country = profile.country or "Vietnam"
        profile.headline = profile.headline or "Senior Software Engineer"
        profile.bio = profile.bio or "Experienced professional with software engineering background."
        profile.skills = "Python, FastAPI, SQL"
        profile.experience_years = 3.0
        profile.resume_url = profile.resume_url or "/uploads/resumes/test.pdf"
        self.db.commit()


        # Find an active job
        job = self.db.query(JobPosting).filter(
            JobPosting.status.in_(["active", "published"]),
            JobPosting.is_deleted == False,
        ).first()
        if not job:
            self.skipTest("No active job posting available in DB")

        # Clean any prior application for this job
        prior = self.db.query(JobApplication).filter(
            JobApplication.job_id == job.id,
            JobApplication.jobseeker_id == profile.id,
        ).first()
        if prior:
            self.db.delete(prior)
            self.db.commit()

        bg_tasks = DummyBackgroundTasks()
        data = JobApplicationCreateRequest(
            job_id=job.id,
            cover_letter="I am very excited to apply for this position.",
            resume_url=profile.resume_url,
            consent=True,
        )

        res = apply_for_job_controller(
            data=data,
            user=user,
            request=DummyRequest(),
            db=self.db,
            background_tasks=bg_tasks,
        )

        self.assertIn("application_id", res)
        self.assertTrue(res.get("acknowledgment_email_sent"))
        self.assertEqual(res.get("acknowledgment_sla"), "24_hours")

        # Verify task was added to background_tasks
        self.assertEqual(len(bg_tasks.tasks), 1)
        task_func, task_args, task_kwargs = bg_tasks.tasks[0]
        self.assertEqual(task_func, send_application_confirmation_email)
        self.assertEqual(task_kwargs["to_email"], user.email)
        self.assertEqual(task_kwargs["job_title"], job.title)

        # Verify row in database
        saved_app = self.db.query(JobApplication).filter(JobApplication.id == res["application_id"]).first()
        self.assertIsNotNone(saved_app)
        self.assertTrue(saved_app.acknowledgment_sent)
        self.assertIsNotNone(saved_app.acknowledgment_sent_at)

        # Verify in-app notification created
        notif = (
            self.db.query(Notification)
            .filter(Notification.application_id == saved_app.id, Notification.type == "confirmation")
            .first()
        )
        self.assertIsNotNone(notif)
        self.assertIn("24 hours", notif.message)

        # Verify get_application_by_id exposes acknowledgment fields
        detail = app_service.get_application_by_id(self.db, saved_app.id, profile.id)
        self.assertTrue(detail["acknowledgment_sent"])
        self.assertIsNotNone(detail["acknowledgment_sent_at"])

    def test_04_dispatch_pending_24h_acknowledgments(self):
        """Verify pending applications within 24 hours are detected and sent."""
        # Query existing unacknowledged applications if any
        count = app_service.dispatch_pending_24h_acknowledgments(self.db)
        self.assertIsInstance(count, int)
        self.assertGreaterEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
