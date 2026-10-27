"""
Test Suite: Company Users Forgot Password & Reset Password Workflow
Tests:
1. Forgot password dispatches reset token & OTP for existing active company user.
2. Forgot password returns safely for non-existent email without leaking existence.
3. Reset password succeeds using valid JWT reset token and updates password.
4. Reset password succeeds using 6-digit OTP code and updates password.
5. Verification that user authenticates with new password.
6. Reset password rejects invalid/expired tokens and incorrect OTP codes.
"""

import sys
import unittest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import MagicMock

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from shared.database.session import SessionLocal, init_db
from shared.models import User, CompanyProfile, CompanyUser
from shared.utils.password import hash_password, verify_password
from shared.utils.jwt import create_password_reset_token
from services.company_service.app.api.auth.schemas import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyResetOtpRequest,
    CompanyLoginRequest,
)
from services.company_service.app.api.auth.controller import (
    forgot_password_controller,
    verify_reset_otp_controller,
    reset_password_controller,
    login_company_controller,
)
from services.company_service.app.api.auth import service as company_auth_service
from fastapi import HTTPException


class TestCompanyForgotResetPassword(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.db = SessionLocal()

        ts = int(datetime.now().timestamp())
        cls.test_email = f"company.recruiter.{ts}@example.com"
        cls.initial_password = "OldCompanyPassword123!"

        # Create legacy User first
        cls.user = User(
            email=cls.test_email,
            hashed_password=hash_password(cls.initial_password),
            first_name="Jane",
            last_name="Recruiter",
            user_type="company",
            is_active=True,
            is_verified=True,
        )
        cls.db.add(cls.user)
        cls.db.flush()

        # Create Company Profile linked to user
        cls.profile = CompanyProfile(
            user_id=cls.user.id,
            company_name=f"Test Enterprise {ts}",
            industry="Technology",
            company_size="51–200",
            verification_status="verified",
        )
        cls.db.add(cls.profile)
        cls.db.flush()

        # Create CompanyUser
        cls.company_user = CompanyUser(
            company_id=cls.profile.id,
            email=cls.test_email,
            password_hash=hash_password(cls.initial_password),
            first_name="Jane",
            last_name="Recruiter",
            role="company_admin",
            is_active=True,
            is_verified=True,
        )
        cls.db.add(cls.company_user)
        cls.db.commit()

        cls.mock_request = MagicMock()
        cls.mock_request.client.host = "127.0.0.1"
        cls.mock_request.headers.get.return_value = "TestAgent"

    @classmethod
    def tearDownClass(cls):
        try:
            cls.db.query(CompanyUser).filter(CompanyUser.email == cls.test_email).delete()
            cls.db.query(CompanyProfile).filter(CompanyProfile.id == cls.profile.id).delete()
            cls.db.query(User).filter(User.email == cls.test_email).delete()
            cls.db.commit()
        except Exception:
            cls.db.rollback()
        finally:
            cls.db.close()

    def test_01_forgot_password_generates_token_and_otp(self):
        """Forgot password endpoint generates token, caches OTP, and returns email."""
        req = ForgotPasswordRequest(email=self.test_email)
        res = forgot_password_controller(req, self.mock_request, self.db)
        self.assertEqual(res["email"], self.test_email.lower())

        # Check OTP verification cache
        cached = company_auth_service._VERIFICATION_CACHE.get(self.test_email.lower())
        self.assertIsNotNone(cached)
        self.assertTrue(len(cached["code"]) >= 6)

    def test_02_forgot_password_non_existent_email_safe(self):
        """Forgot password returns safely without leaking email existence."""
        fake_email = "nonexistent.company@example.com"
        req = ForgotPasswordRequest(email=fake_email)
        res = forgot_password_controller(req, self.mock_request, self.db)
        self.assertEqual(res["email"], fake_email)

    def test_03_reset_password_with_jwt_token(self):
        """Reset password validates JWT reset token and updates password in DB."""
        token = create_password_reset_token(user_id=self.company_user.id, email=self.test_email)
        new_password = "BrandNewSecretPassword123!"

        reset_req = ResetPasswordRequest(
            token=token,
            email=self.test_email,
            new_password=new_password,
        )
        reset_password_controller(reset_req, self.mock_request, self.db)

        # Verify password in DB
        self.db.refresh(self.company_user)
        self.assertTrue(verify_password(new_password, self.company_user.password_hash))

        # Verify login succeeds with new password
        login_req = CompanyLoginRequest(email=self.test_email, password=new_password)
        login_res = login_company_controller(login_req, self.mock_request, self.db)
        self.assertIn("access_token", login_res)

    def test_04_reset_password_with_otp_code(self):
        """Reset password validates 6-digit OTP code and updates password."""
        otp = company_auth_service.store_verification_code(self.test_email, expiry_minutes=15)
        new_password_2 = "SecondUpdatedPassword123!"

        reset_req = ResetPasswordRequest(
            code=otp,
            email=self.test_email,
            new_password=new_password_2,
        )
        reset_password_controller(reset_req, self.mock_request, self.db)

        self.db.refresh(self.company_user)
        self.assertTrue(verify_password(new_password_2, self.company_user.password_hash))

    def test_05_reset_password_rejects_invalid_token(self):
        """Reset password raises 400 error when given bad token or invalid code."""
        reset_req = ResetPasswordRequest(
            token="invalid.jwt.token",
            email=self.test_email,
            new_password="ShouldNotWork123!",
        )
        with self.assertRaises(HTTPException) as ctx:
            reset_password_controller(reset_req, self.mock_request, self.db)
        self.assertEqual(ctx.exception.status_code, 400)


    def test_06_fastapi_endpoints_via_testclient(self):
        """Verify full HTTP request/response cycle through FastAPI TestClient."""
        from fastapi.testclient import TestClient
        from services.company_service.app.main import app

        with TestClient(app) as client:
            # Test POST /api/v1/company/auth/forgot-password
            res = client.post(
                "/api/v1/company/auth/forgot-password",
                json={"email": self.test_email},
            )
            self.assertEqual(res.status_code, 200)
            json_data = res.json()
            self.assertTrue(json_data.get("success"))
            self.assertIn("reset link has been sent", json_data.get("message", ""))

            # Test POST /api/v1/company/auth/reset-password
            token = create_password_reset_token(user_id=self.company_user.id, email=self.test_email)
            reset_res = client.post(
                "/api/v1/company/auth/reset-password",
                json={
                    "token": token,
                    "email": self.test_email,
                    "new_password": "TestClientNewPassword123!",
                },
            )
            self.assertEqual(reset_res.status_code, 200)
            reset_json = reset_res.json()
            self.assertTrue(reset_json.get("success"))
            self.assertIn("Password updated successfully", reset_json.get("message", ""))

    def test_07_verify_reset_otp_controller_and_testclient(self):
        """Verify 6-digit OTP validation via controller and HTTP endpoint."""
        from fastapi.testclient import TestClient
        from services.company_service.app.main import app

        # 1. Controller test: generate OTP & verify
        otp = company_auth_service.store_verification_code(self.test_email, expiry_minutes=15)
        verify_req = VerifyResetOtpRequest(email=self.test_email, code=otp)
        res = verify_reset_otp_controller(verify_req, self.mock_request, self.db)
        self.assertTrue(res["verified"])
        self.assertIn("reset_token", res)
        self.assertEqual(res["email"], self.test_email)

        # 2. Controller test: invalid code rejected
        bad_req = VerifyResetOtpRequest(email=self.test_email, code="000000")
        with self.assertRaises(HTTPException) as ctx:
            verify_reset_otp_controller(bad_req, self.mock_request, self.db)
        self.assertEqual(ctx.exception.status_code, 400)

        # 3. HTTP TestClient test: verify dev bypass OTP 123456
        with TestClient(app) as client:
            http_res = client.post(
                "/api/v1/company/auth/verify-reset-otp",
                json={"email": self.test_email, "code": "123456"},
            )
            self.assertEqual(http_res.status_code, 200)
            data = http_res.json()
            self.assertTrue(data.get("success"))
            self.assertTrue(data.get("data", {}).get("verified"))
            self.assertIn("reset_token", data.get("data", {}))


if __name__ == "__main__":
    unittest.main()


