"""
Test Suite: Profile Visibility & Job Availability (BR-101-07 & BR-101-08)
Tests:
1. Schema verification: job_availability column exists on JobSeekerProfile with default "open_to_work".
2. Immediate update: update_profile_and_user immediately persists job_availability and visibility without delay (BR-101-07).
3. Schema validation: JobSeekerProfileUpdateSchema strictly allows ["open_to_work", "open_to_opportunities", "not_looking"] and rejects invalid values.
4. 12-Month Inactive Archiving (BR-101-08): auto_archive_inactive_profiles sets is_archived=True, is_visible=False, and job_availability="not_looking".
5. Candidate Re-login Unarchiving: Logging in after being archived automatically restores is_archived=False, is_visible=True, and sets job_availability="open_to_opportunities".
6. Company ATS Candidate Visibility: Company applicant service serializer includes job_availability and jobAvailability.
"""

import sys
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from pydantic import ValidationError
from shared.database.session import SessionLocal, init_db
from shared.models import User, JobSeekerProfile, CompanyProfile, JobPosting, JobApplication
from shared.utils.password import hash_password
from services.jobseeker_service.app.api.profile import service as profile_service
from services.jobseeker_service.app.api.profile.schemas import JobSeekerProfileUpdateSchema
from services.jobseeker_service.app.api.auth.controller import login_jobseeker_controller
from services.jobseeker_service.app.api.auth.schemas import JobSeekerLoginRequest
from services.company_service.app.api.applicants import service as applicant_service


class TestProfileVisibilityJobAvailability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.db = SessionLocal()

        # Create dedicated test candidate
        test_email = f"test.availability.{datetime.now().timestamp()}@example.com"
        cls.test_user = User(
            email=test_email,
            hashed_password=hash_password("Password123!"),
            full_name="Availability Test User",
            user_type="jobseeker",
            is_active=True,
            is_verified=True,
            last_login=datetime.now(timezone.utc),
        )
        cls.db.add(cls.test_user)
        cls.db.flush()

        cls.test_profile = JobSeekerProfile(
            user_id=cls.test_user.id,
            headline="Full Stack Automated Tester",
            bio="Dedicated to verifying BR-101-07 and BR-101-08 requirements.",
            skills="Python, FastAPI, Jest, React",
            experience_years=5.0,
            expected_salary=30000000.0,
            city="Ho Chi Minh City",
            is_visible=True,
            visibility="public",
            job_availability="open_to_work",
        )
        cls.db.add(cls.test_profile)
        cls.db.commit()
        cls.db.refresh(cls.test_user)
        cls.db.refresh(cls.test_profile)

    @classmethod
    def tearDownClass(cls):
        try:
            # Clean up test user & profile
            cls.db.delete(cls.test_profile)
            cls.db.delete(cls.test_user)
            cls.db.commit()
        except Exception:
            cls.db.rollback()
        finally:
            cls.db.close()

    def test_01_schema_has_job_availability(self):
        """Verify JobSeekerProfile model schema definition and default values."""
        self.assertIn("job_availability", JobSeekerProfile.__table__.columns)
        col = JobSeekerProfile.__table__.columns["job_availability"]
        self.assertFalse(col.nullable)
        self.assertEqual(col.default.arg, "open_to_work")

    def test_02_job_availability_schema_validation(self):
        """Verify JobSeekerProfileUpdateSchema accepts valid availability and rejects invalid values."""
        valid_options = ["open_to_work", "open_to_opportunities", "not_looking"]
        for opt in valid_options:
            schema = JobSeekerProfileUpdateSchema(job_availability=opt)
            self.assertEqual(schema.job_availability, opt)

        # Invalid option must raise ValidationError
        with self.assertRaises(ValidationError):
            JobSeekerProfileUpdateSchema(job_availability="available_next_month")

    def test_03_immediate_profile_visibility_update_br_101_07(self):
        """Verify changes to visibility and is_visible take effect immediately without delays."""
        # 1. Update to recruiter_only & not visible
        u, p = profile_service.update_profile_and_user(
            self.db,
            self.test_user,
            self.test_profile,
            {"visibility": "recruiter_only", "is_visible": False}
        )
        serialized = profile_service.serialize_profile(u, p)
        self.assertEqual(serialized["visibility"], "recruiter_only")
        self.assertEqual(serialized["is_visible"], False)

        # Confirm live database state
        self.db.refresh(self.test_profile)
        self.assertEqual(self.test_profile.visibility, "recruiter_only")
        self.assertFalse(self.test_profile.is_visible)

        # 2. Update immediately back to public & visible
        u2, p2 = profile_service.update_profile_and_user(
            self.db,
            self.test_user,
            self.test_profile,
            {"visibility": "public", "is_visible": True}
        )
        serialized2 = profile_service.serialize_profile(u2, p2)
        self.assertEqual(serialized2["visibility"], "public")
        self.assertEqual(serialized2["is_visible"], True)

        self.db.refresh(self.test_profile)
        self.assertEqual(self.test_profile.visibility, "public")
        self.assertTrue(self.test_profile.is_visible)

    def test_04_immediate_job_availability_transitions(self):
        """Verify job availability transitions immediately across all 3 valid states."""
        # Transition 1: open_to_opportunities (Yellow)
        u1, p1 = profile_service.update_profile_and_user(
            self.db,
            self.test_user,
            self.test_profile,
            {"job_availability": "open_to_opportunities"}
        )
        ser1 = profile_service.serialize_profile(u1, p1)
        self.assertEqual(ser1["job_availability"], "open_to_opportunities")
        self.db.refresh(self.test_profile)
        self.assertEqual(self.test_profile.job_availability, "open_to_opportunities")

        # Transition 2: not_looking (Red)
        u2, p2 = profile_service.update_profile_and_user(
            self.db,
            self.test_user,
            self.test_profile,
            {"job_availability": "not_looking"}
        )
        ser2 = profile_service.serialize_profile(u2, p2)
        self.assertEqual(ser2["job_availability"], "not_looking")
        self.db.refresh(self.test_profile)
        self.assertEqual(self.test_profile.job_availability, "not_looking")

        # Transition 3: open_to_work (Green)
        u3, p3 = profile_service.update_profile_and_user(
            self.db,
            self.test_user,
            self.test_profile,
            {"job_availability": "open_to_work"}
        )
        ser3 = profile_service.serialize_profile(u3, p3)
        self.assertEqual(ser3["job_availability"], "open_to_work")
        self.db.refresh(self.test_profile)
        self.assertEqual(self.test_profile.job_availability, "open_to_work")

    def test_05_auto_archive_inactive_profiles_br_101_08(self):
        """Verify BR-101-08: profiles inactive for > 12 months are archived and set to not_looking."""
        # Create an inactive user (> 12 months ago)
        inactive_email = f"inactive.{datetime.now().timestamp()}@example.com"
        thirteen_months_ago = datetime.now(timezone.utc) - timedelta(days=395)
        inactive_user = User(
            email=inactive_email,
            hashed_password=hash_password("Password123!"),
            full_name="Inactive Candidate",
            user_type="jobseeker",
            is_active=True,
            is_verified=True,
            last_login=thirteen_months_ago,
        )
        self.db.add(inactive_user)
        self.db.flush()

        inactive_profile = JobSeekerProfile(
            user_id=inactive_user.id,
            headline="Inactive Candidate Headline",
            is_visible=True,
            is_archived=False,
            job_availability="open_to_work",
        )
        self.db.add(inactive_profile)
        self.db.commit()

        try:
            # Run auto-archiving service
            archived_count = profile_service.auto_archive_inactive_profiles(self.db)
            self.assertGreaterEqual(archived_count, 1)

            # Check profile state
            self.db.refresh(inactive_profile)
            self.assertTrue(inactive_profile.is_archived)
            self.assertFalse(inactive_profile.is_visible)
            self.assertEqual(inactive_profile.job_availability, "not_looking")

            # Test Candidate Login unarchives and sets to open_to_opportunities
            class MockClient:
                host = "127.0.0.1"

            class MockRequest:
                headers = {"user-agent": "automated-test"}
                client = MockClient()

            login_data = JobSeekerLoginRequest(email=inactive_email, password="Password123!")
            login_resp = login_jobseeker_controller(login_data, MockRequest(), self.db)
            self.assertIn("access_token", login_resp)

            # Verify unarchived state
            self.db.refresh(inactive_user)
            self.db.refresh(inactive_profile)
            self.assertFalse(inactive_profile.is_archived)
            self.assertTrue(inactive_profile.is_visible)
            self.assertEqual(inactive_profile.job_availability, "open_to_opportunities")

        finally:
            self.db.delete(inactive_profile)
            self.db.delete(inactive_user)
            self.db.commit()

    def test_06_company_applicant_serializer_contains_job_availability(self):
        """Verify Company applicant serialization includes job_availability and jobAvailability."""
        company = self.db.query(CompanyProfile).first()
        if company:
            items, total = applicant_service.list_company_applicants(self.db, company.id)
            if items:
                applicant_dict = items[0]
                self.assertIn("job_availability", applicant_dict)
                self.assertIn("jobAvailability", applicant_dict)
                self.assertIn("is_visible", applicant_dict)
                self.assertIn(applicant_dict["job_availability"], ["open_to_work", "open_to_opportunities", "not_looking"])


if __name__ == "__main__":
    unittest.main()
