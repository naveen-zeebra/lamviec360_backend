import os
import sys
from pathlib import Path
import tempfile
import unittest

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from services.jobseeker_service.app.main import app
from shared.utils import get_current_jobseeker
from shared.database.session import get_db
from shared.models import User, JobSeekerProfile, JobSeekerResume, JobSeekerDocument

class TestDownloadEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.mock_user = MagicMock(spec=User)
        self.mock_user.id = 10
        self.mock_user.role = "jobseeker"
        self.mock_user.email = "candidate@example.com"

        self.mock_profile = MagicMock(spec=JobSeekerProfile)
        self.mock_profile.id = 20
        self.mock_profile.user_id = 10

        app.dependency_overrides[get_current_jobseeker] = lambda: self.mock_user
        app.dependency_overrides[get_db] = lambda: MagicMock()

    def tearDown(self):
        app.dependency_overrides.clear()

    @patch("services.jobseeker_service.app.api.profile.service.get_or_create_jobseeker_profile")
    @patch("services.jobseeker_service.app.api.profile.resume_service.download_path_for_resume")
    def test_download_resume_attachment_header(self, mock_download_path, mock_get_profile):
        mock_get_profile.return_value = self.mock_profile
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4 test resume content")
            tmp_path = tmp.name

        try:
            mock_row = MagicMock(spec=JobSeekerResume)
            mock_row.file_name = "my_cv_2026.pdf"
            mock_row.mime_type = "application/pdf"
            mock_download_path.return_value = (tmp_path, mock_row)

            res = self.client.get("/api/v1/jobseeker/profile/resumes/1/download")
            self.assertEqual(res.status_code, 200)
            self.assertIn("attachment", res.headers.get("content-disposition", ""))
            self.assertIn("my_cv_2026.pdf", res.headers.get("content-disposition", ""))
            self.assertEqual(res.headers.get("content-type"), "application/pdf")
            self.assertEqual(res.content, b"%PDF-1.4 test resume content")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @patch("services.jobseeker_service.app.api.profile.service.get_or_create_jobseeker_profile")
    @patch("services.jobseeker_service.app.api.profile.document_service.get_document_download")
    def test_download_candidate_document_attachment_header(self, mock_doc_download, mock_get_profile):
        mock_get_profile.return_value = self.mock_profile
        
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp.write(b"PK test docx content")
            tmp_path = tmp.name

        try:
            mock_row = MagicMock(spec=JobSeekerDocument)
            mock_row.file_name = "labor_contract.docx"
            mock_row.mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            mock_doc_download.return_value = (tmp_path, mock_row)

            res = self.client.get("/api/v1/jobseeker/profile/documents/5/download")
            self.assertEqual(res.status_code, 200)
            self.assertIn("attachment", res.headers.get("content-disposition", ""))
            self.assertIn("labor_contract.docx", res.headers.get("content-disposition", ""))
            self.assertEqual(res.content, b"PK test docx content")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

if __name__ == "__main__":
    unittest.main()
