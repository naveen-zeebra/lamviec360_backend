import os
import unittest
from unittest.mock import patch

from shared.config.upload_config import (
    UPLOAD_CONFIG,
    AvatarConfig,
    ResumeConfig,
    CertificationConfig,
    DocumentArchiveConfig,
    CompanyMediaConfig,
    ProfileAttachmentQuotaConfig,
    UploadConfig,
)
from shared.utils.resume_storage import (
    MAX_RESUME_BYTES,
    MAX_RESUMES_PER_SEEKER,
    ALLOWED_RESUME_EXT,
    MIME_BY_EXT,
    MAX_RESUME_ERROR,
)
from services.jobseeker_service.app.api.profile.document_service import (
    MAX_DOC_BYTES,
    MAX_STORAGE_QUOTA_BYTES,
    ALLOWED_DOC_EXT,
    ALLOWED_CATEGORIES,
)


class TestUploadConfig(unittest.TestCase):
    def test_upload_config_defaults(self):
        """Verify default limits and byte calculations."""
        self.assertEqual(UPLOAD_CONFIG.avatar.max_size_mb, 2)
        self.assertEqual(UPLOAD_CONFIG.avatar.max_size_bytes, 2 * 1024 * 1024)
        self.assertIn(".jpg", UPLOAD_CONFIG.avatar.allowed_extensions)
        self.assertIn("2MB", UPLOAD_CONFIG.avatar.max_size_error_message)

        self.assertEqual(UPLOAD_CONFIG.resume.max_size_mb, 5)
        self.assertEqual(UPLOAD_CONFIG.resume.max_size_bytes, 5 * 1024 * 1024)
        self.assertEqual(UPLOAD_CONFIG.resume.max_count, 5)
        self.assertIn(".pdf", UPLOAD_CONFIG.resume.allowed_extensions)
        self.assertIn("5 MB", UPLOAD_CONFIG.resume.max_size_error_message)

        self.assertEqual(UPLOAD_CONFIG.certification.max_size_mb, 5)
        self.assertEqual(UPLOAD_CONFIG.certification.max_size_bytes, 5 * 1024 * 1024)

        # Cumulative Profile Attachment Quota: 10MB max
        self.assertEqual(UPLOAD_CONFIG.profile_attachment_quota.max_total_mb, 10)
        self.assertEqual(UPLOAD_CONFIG.profile_attachment_quota.max_total_bytes, 10 * 1024 * 1024)
        self.assertIn("10MB", UPLOAD_CONFIG.profile_attachment_quota.error_message_en)
        self.assertIn("10MB", UPLOAD_CONFIG.profile_attachment_quota.error_message_vi)

        self.assertEqual(UPLOAD_CONFIG.document_archive.max_size_mb, 10)
        self.assertEqual(UPLOAD_CONFIG.document_archive.max_size_bytes, 10 * 1024 * 1024)
        self.assertEqual(UPLOAD_CONFIG.document_archive.quota_mb, 100)
        self.assertEqual(UPLOAD_CONFIG.document_archive.quota_bytes, 100 * 1024 * 1024)
        self.assertIn("contract", UPLOAD_CONFIG.document_archive.allowed_categories)
        self.assertIn("certificate", UPLOAD_CONFIG.document_archive.allowed_categories)

        self.assertEqual(UPLOAD_CONFIG.company.logo_max_size_mb, 5)
        self.assertEqual(UPLOAD_CONFIG.company.banner_max_size_mb, 10)

    def test_backward_compatibility_aliases(self):
        """Verify that existing legacy constant names are fully preserved."""
        self.assertEqual(MAX_RESUMES_PER_SEEKER, UPLOAD_CONFIG.resume.max_count)
        self.assertEqual(MAX_RESUME_BYTES, UPLOAD_CONFIG.resume.max_size_bytes)
        self.assertEqual(ALLOWED_RESUME_EXT, UPLOAD_CONFIG.resume.allowed_extensions)
        self.assertEqual(MIME_BY_EXT, UPLOAD_CONFIG.resume.mime_by_ext)
        self.assertEqual(MAX_RESUME_ERROR, UPLOAD_CONFIG.resume.max_count_error_message)

        self.assertEqual(MAX_DOC_BYTES, UPLOAD_CONFIG.document_archive.max_size_bytes)
        self.assertEqual(MAX_STORAGE_QUOTA_BYTES, UPLOAD_CONFIG.document_archive.quota_bytes)
        self.assertEqual(ALLOWED_DOC_EXT, UPLOAD_CONFIG.document_archive.allowed_extensions_list)
        self.assertEqual(ALLOWED_CATEGORIES, UPLOAD_CONFIG.document_archive.allowed_categories)

    def test_env_variable_overrides(self):
        """Verify that environment variables dynamically override limits."""
        env_vars = {
            "MAX_AVATAR_SIZE_MB": "4",
            "MAX_RESUME_SIZE_MB": "8",
            "MAX_RESUMES_PER_SEEKER": "10",
            "MAX_DOCUMENT_SIZE_MB": "25",
        }
        with patch.dict(os.environ, env_vars):
            custom_cfg = UploadConfig(
                avatar=AvatarConfig(),
                resume=ResumeConfig(),
                certification=CertificationConfig(),
                document_archive=DocumentArchiveConfig(),
                company=CompanyMediaConfig(),
            )

            self.assertEqual(custom_cfg.avatar.max_size_mb, 4)
            self.assertEqual(custom_cfg.avatar.max_size_bytes, 4 * 1024 * 1024)
            self.assertIn("4MB", custom_cfg.avatar.max_size_error_message)

            self.assertEqual(custom_cfg.resume.max_size_mb, 8)
            self.assertEqual(custom_cfg.resume.max_size_bytes, 8 * 1024 * 1024)
            self.assertEqual(custom_cfg.resume.max_count, 10)

            self.assertEqual(custom_cfg.document_archive.max_size_mb, 25)
            self.assertEqual(custom_cfg.document_archive.max_size_bytes, 25 * 1024 * 1024)

    def test_to_frontend_dict_format(self):
        """Verify JSON structure emitted by to_frontend_dict()."""
        frontend_data = UPLOAD_CONFIG.to_frontend_dict()
        self.assertIn("AVATAR", frontend_data)
        self.assertIn("RESUME", frontend_data)
        self.assertIn("CERTIFICATION", frontend_data)
        self.assertIn("DOCUMENT_ARCHIVE", frontend_data)
        self.assertIn("COMPANY", frontend_data)
        self.assertIn("PROFILE_ATTACHMENT_QUOTA", frontend_data)

        self.assertEqual(frontend_data["PROFILE_ATTACHMENT_QUOTA"]["maxMb"], 10)
        self.assertEqual(frontend_data["PROFILE_ATTACHMENT_QUOTA"]["maxBytes"], 10 * 1024 * 1024)
        self.assertIn("10MB", frontend_data["PROFILE_ATTACHMENT_QUOTA"]["errorEn"])
        self.assertIn("10MB", frontend_data["PROFILE_ATTACHMENT_QUOTA"]["errorVi"])

        self.assertEqual(frontend_data["AVATAR"]["maxMb"], 2)
        self.assertEqual(frontend_data["AVATAR"]["maxBytes"], 2 * 1024 * 1024)
        self.assertIn(".jpg", frontend_data["AVATAR"]["extensions"])

        self.assertEqual(frontend_data["RESUME"]["maxMb"], 5)
        self.assertEqual(frontend_data["RESUME"]["maxCount"], 5)
        self.assertIn(".pdf", frontend_data["RESUME"]["extensions"])

        self.assertEqual(frontend_data["DOCUMENT_ARCHIVE"]["maxMb"], 10)
        self.assertEqual(frontend_data["DOCUMENT_ARCHIVE"]["quotaMb"], 100)
        self.assertIn("contract", frontend_data["DOCUMENT_ARCHIVE"]["categories"])
        self.assertIn("relieving", frontend_data["DOCUMENT_ARCHIVE"]["categories"])
        self.assertIn("payslip", frontend_data["DOCUMENT_ARCHIVE"]["categories"])
        self.assertIn("certificate", frontend_data["DOCUMENT_ARCHIVE"]["categories"])
        self.assertIn("other", frontend_data["DOCUMENT_ARCHIVE"]["categories"])

    def test_dynamic_endpoint(self):
        """Test GET /api/v1/jobseeker/profile/upload-config via FastAPI TestClient."""
        from fastapi.testclient import TestClient
        from services.jobseeker_service.app.main import app

        client = TestClient(app)
        response = client.get("/api/v1/jobseeker/profile/upload-config")
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertTrue(json_data.get("success"))
        data = json_data.get("data")
        self.assertEqual(data["AVATAR"]["maxMb"], 2)
        self.assertEqual(data["RESUME"]["maxMb"], 5)
        self.assertEqual(data["PROFILE_ATTACHMENT_QUOTA"]["maxMb"], 10)
        self.assertEqual(data["DOCUMENT_ARCHIVE"]["quotaMb"], 100)
        self.assertIn("relieving", data["DOCUMENT_ARCHIVE"]["categories"])

    def test_document_category_normalization(self):
        """Test that categories like relieving and relieving_letter are normalized properly."""
        from services.jobseeker_service.app.api.profile.document_service import ALLOWED_CATEGORIES
        self.assertIn("contract", ALLOWED_CATEGORIES)
        self.assertIn("relieving", ALLOWED_CATEGORIES)
        self.assertIn("payslip", ALLOWED_CATEGORIES)
        self.assertIn("certificate", ALLOWED_CATEGORIES)
        self.assertIn("other", ALLOWED_CATEGORIES)


if __name__ == "__main__":
    unittest.main()
