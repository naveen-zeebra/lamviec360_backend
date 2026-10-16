import unittest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from services.jobseeker_service.app.main import app
from services.jobseeker_service.app.api.profile import document_service
from shared.models import JobSeekerProfile, User

class TestDocumentCategoryUpload(unittest.TestCase):
    def test_category_normalization_and_serialization(self):
        """Test document_service normalization and serialization of categories."""
        # Test relieving_letter normalizes to relieving
        mock_doc = MagicMock()
        mock_doc.id = 101
        mock_doc.category = "relieving_letter"
        mock_doc.title = "Relieving Letter"
        mock_doc.file_name = "relieving.pdf"
        mock_doc.file_url = "/uploads/documents/1/relieving.pdf"
        mock_doc.mime_type = "application/pdf"
        mock_doc.size_bytes = 1024
        mock_doc.created_at = None
        mock_doc.updated_at = None

        serialized = document_service.serialize_document(mock_doc)
        self.assertEqual(serialized["category"], "relieving")

    def test_allowed_categories_contains_all_frontend_ids(self):
        """Ensure all frontend category tabs are accepted by backend."""
        from shared.config.upload_config import UPLOAD_CONFIG
        allowed = UPLOAD_CONFIG.document_archive.allowed_categories
        for cat in ["contract", "relieving", "payslip", "certificate", "other"]:
            self.assertIn(cat, allowed)

if __name__ == "__main__":
    unittest.main()
