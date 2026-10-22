import unittest
from unittest.mock import patch, MagicMock
from io import BytesIO
from fastapi.testclient import TestClient
from fastapi import UploadFile

from shared.database.session import SessionLocal, init_db
from shared.models import User, JobSeekerProfile, JobSeekerDocument, JobApplication, JobPosting, CompanyProfile
from services.jobseeker_service.app.main import app as jobseeker_app
from services.company_service.app.main import app as company_app
from shared.utils.document_encryption import (
    encrypt_document_data,
    decrypt_document_data,
    hash_archive_pin,
    verify_archive_pin,
    is_encrypted_document,
)
from services.jobseeker_service.app.api.profile import document_service
from services.company_service.app.api.applicants import service as company_service_applicant


class TestDocumentEncryptionAndVisibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.db = SessionLocal()
        self.jobseeker_client = TestClient(jobseeker_app)
        self.company_client = TestClient(company_app)

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_01_encryption_utility_encrypt_decrypt_and_integrity(self):
        """Verify AES authenticated encryption, tampering detection, and PIN salt."""
        raw_text = b"CONFIDENTIAL EMPLOYMENT CONTRACT 2026 - SALARY 50,000,000 VND"
        encrypted = encrypt_document_data(raw_text)

        self.assertTrue(is_encrypted_document(encrypted))
        self.assertNotEqual(encrypted, raw_text)
        self.assertNotIn(b"CONFIDENTIAL", encrypted)

        # Decrypt without PIN
        decrypted = decrypt_document_data(encrypted)
        self.assertEqual(decrypted, raw_text)

        # Encrypt with PIN
        pin = "998877"
        encrypted_with_pin = encrypt_document_data(raw_text, user_pin=pin)
        self.assertTrue(is_encrypted_document(encrypted_with_pin))
        decrypted_pin = decrypt_document_data(encrypted_with_pin, user_pin=pin)
        self.assertEqual(decrypted_pin, raw_text)

        # Wrong PIN should fail
        with self.assertRaises(Exception):
            decrypt_document_data(encrypted_with_pin, user_pin="wrong_pin")

    def test_02_archive_pin_hashing_and_verification(self):
        """Verify PIN hashing with PBKDF2-HMAC-SHA256."""
        pin = "123456"
        hashed = hash_archive_pin(pin)
        self.assertTrue(hashed.startswith("pbkdf2_sha256$100000$"))
        self.assertTrue(verify_archive_pin(pin, hashed))
        self.assertFalse(verify_archive_pin("654321", hashed))
        self.assertFalse(verify_archive_pin("", hashed))

    def test_03_jobseeker_upload_document_is_encrypted_on_disk(self):
        """Verify add_document encrypts file bytes on physical disk per JSP-FR-012."""
        seeker_user = self.db.query(User).filter_by(email="seeker.python.dev@yopmail.com").first()
        if not seeker_user:
            self.skipTest("seeker.python.dev@yopmail.com not found")
        profile = self.db.query(JobSeekerProfile).filter_by(user_id=seeker_user.id).first()

        doc_content = b"PDF_HEADER_%PDF-1.4 Relieving letter from TechCorp Vietnam."
        upload = UploadFile(filename="relieving_letter.pdf", file=BytesIO(doc_content))

        doc = document_service.add_document(
            db=self.db,
            profile=profile,
            upload=upload,
            category="relieving",
            title="Relieving Letter TechCorp",
        )

        self.assertTrue(doc.is_encrypted)
        self.assertEqual(doc.category, "relieving")

        # Verify physical file on disk is encrypted
        target, row = document_service.get_document_download(self.db, profile, doc.id)
        raw_disk_bytes = target.read_bytes()
        self.assertTrue(is_encrypted_document(raw_disk_bytes))
        self.assertNotIn(b"Relieving letter from TechCorp", raw_disk_bytes)

        # Verify decrypted download returns original content
        decrypted, _ = document_service.get_document_decrypted_content(self.db, profile, doc.id)
        self.assertEqual(decrypted, doc_content)

        # Clean up
        document_service.delete_document(self.db, profile, doc.id)

    def test_04_archive_pin_lock_and_unlock(self):
        """Verify candidate can set PIN, lock archive, and unlock."""
        seeker_user = self.db.query(User).filter_by(email="seeker.python.dev@yopmail.com").first()
        if not seeker_user:
            self.skipTest("seeker.python.dev@yopmail.com not found")
        profile = self.db.query(JobSeekerProfile).filter_by(user_id=seeker_user.id).first()

        # Reset profile PIN hash if present from previous test runs
        profile.archive_pin_hash = None
        profile.is_archive_locked = False
        self.db.commit()

        # Set PIN
        pin = "556677"
        document_service.set_archive_pin(self.db, profile, new_pin=pin)
        self.assertTrue(profile.is_archive_locked)
        self.assertTrue(bool(profile.archive_pin_hash))

        # Unlock with valid PIN
        document_service.verify_archive_pin_service(self.db, profile, pin=pin)
        self.assertFalse(profile.is_archive_locked)

        # Lock again
        document_service.lock_archive(self.db, profile)
        self.assertTrue(profile.is_archive_locked)

        # Remove PIN
        document_service.remove_archive_pin(self.db, profile, current_pin=pin)
        self.assertFalse(profile.is_archive_locked)
        self.assertIsNone(profile.archive_pin_hash)

    def test_06_download_pin_verification_and_unlocked_session(self):
        """Verify downloading document when archive is unlocked vs locked with PIN."""
        seeker_user = self.db.query(User).filter_by(email="seeker.python.dev@yopmail.com").first()
        profile = self.db.query(JobSeekerProfile).filter_by(user_id=seeker_user.id).first()

        doc_content = b"%PDF-1.4 Relieving letter TechCorp Decrypt Test"
        upload = UploadFile(filename="decrypt_test.pdf", file=BytesIO(doc_content))
        doc = document_service.add_document(
            db=self.db,
            profile=profile,
            upload=upload,
            category="relieving",
            title="Decrypt Test",
        )

        pin = "112233"
        document_service.set_archive_pin(self.db, profile, new_pin=pin)
        self.assertTrue(profile.is_archive_locked)

        try:
            # 1. Archive is locked, no PIN -> raises 401
            with self.assertRaises(Exception) as ctx:
                document_service.get_document_download(self.db, profile, doc.id, pin=None)
            self.assertIn("Security PIN required", str(ctx.exception.detail))

            # 2. Archive is locked, wrong PIN -> raises 401
            with self.assertRaises(Exception) as ctx:
                document_service.get_document_download(self.db, profile, doc.id, pin="999999")
            self.assertIn("Invalid Security PIN", str(ctx.exception.detail))

            # 3. Archive is locked, correct PIN -> succeeds and decrypts!
            target, row = document_service.get_document_download(self.db, profile, doc.id, pin=pin)
            decrypted = decrypt_document_data(target.read_bytes(), user_pin=pin)
            self.assertEqual(decrypted, doc_content)

            # 4. Unlock archive session
            document_service.verify_archive_pin_service(self.db, profile, pin=pin)
            self.assertFalse(profile.is_archive_locked)

            # 5. Archive is unlocked -> download without passing PIN succeeds!
            target_unlocked, row_unlocked = document_service.get_document_download(self.db, profile, doc.id, pin=None)
            decrypted_unlocked = decrypt_document_data(target_unlocked.read_bytes(), user_pin=None)
            self.assertEqual(decrypted_unlocked, doc_content)

        finally:
            document_service.delete_document(self.db, profile, doc.id)
            document_service.remove_archive_pin(self.db, profile, current_pin=pin)

    def test_05_employer_visibility_rule_emp_fr_026b(self):
        """
        Verify EMP-FR-026b:
        - Applied / Screening: 403 Forbidden
        - Shortlisted, Interviewing, Offered, Hired: 200 OK + access to decrypted documents
        - Rejected: 403 Forbidden
        """
        company_prof = self.db.query(CompanyProfile).first()
        if not company_prof:
            self.skipTest("No company profile found")

        job = self.db.query(JobPosting).filter_by(company_id=company_prof.id, is_deleted=False).first()
        if not job:
            self.skipTest("No job posting found for company")

        seeker_prof = self.db.query(JobSeekerProfile).first()
        if not seeker_prof:
            self.skipTest("No seeker profile found")

        # Upload a test document for candidate
        doc_content = b"%PDF-1.4 Payslip TechCorp - Salary 45M VND"
        upload = UploadFile(filename="payslip_nov_2025.pdf", file=BytesIO(doc_content))
        doc = document_service.add_document(
            db=self.db,
            profile=seeker_prof,
            upload=upload,
            category="payslip",
            title="TechCorp Payslip Nov 2025",
        )

        # Create or fetch an application
        app = (
            self.db.query(JobApplication)
            .filter_by(job_id=job.id, jobseeker_id=seeker_prof.id)
            .first()
        )
        if not app:
            app = JobApplication(
                job_id=job.id,
                jobseeker_id=seeker_prof.id,
                status="applied",
            )
            self.db.add(app)
            self.db.commit()
            self.db.refresh(app)

        try:
            # 1. Stage: applied -> must raise 403 Forbidden
            app.status = "applied"
            self.db.commit()
            with self.assertRaises(Exception) as ctx:
                company_service_applicant.get_applicant_verification_documents(
                    self.db, company_prof.id, app.id
                )
            self.assertIn("Shortlisted stage onward", str(ctx.exception.detail))

            # 2. Stage: screening -> must raise 403 Forbidden
            app.status = "screening"
            self.db.commit()
            with self.assertRaises(Exception) as ctx:
                company_service_applicant.get_applicant_verification_documents(
                    self.db, company_prof.id, app.id
                )
            self.assertIn("Shortlisted stage onward", str(ctx.exception.detail))

            # 3. Stage: Shortlisted -> must return 200 OK with document list!
            app.status = "shortlisted"
            self.db.commit()
            result = company_service_applicant.get_applicant_verification_documents(
                self.db, company_prof.id, app.id
            )
            self.assertTrue(result["can_access"])
            self.assertGreaterEqual(len(result["documents"]), 1)
            found = any(d["id"] == doc.id for d in result["documents"])
            self.assertTrue(found)

            # Download as employer while shortlisted -> decrypted bytes match!
            decrypted_employer, downloaded_doc = company_service_applicant.download_applicant_verification_document(
                self.db, company_prof.id, app.id, doc.id
            )
            self.assertEqual(decrypted_employer, doc_content)

            # 4. Stage: interviewing -> must also allow access
            app.status = "interviewing"
            self.db.commit()
            result_interview = company_service_applicant.get_applicant_verification_documents(
                self.db, company_prof.id, app.id
            )
            self.assertTrue(result_interview["can_access"])

            # 5. Stage: rejected -> access immediately revoked (403 Forbidden)
            app.status = "rejected"
            self.db.commit()
            with self.assertRaises(Exception) as ctx:
                company_service_applicant.get_applicant_verification_documents(
                    self.db, company_prof.id, app.id
                )
            self.assertIn("Shortlisted stage onward", str(ctx.exception.detail))

        finally:
            document_service.delete_document(self.db, seeker_prof, doc.id)


if __name__ == "__main__":
    unittest.main()
