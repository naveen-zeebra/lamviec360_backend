import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_seeker_registration_and_login(client):
    email = "newseeker@example.com"
    # 1. Register Seeker
    reg_payload = {
        "name": "Test Seeker",
        "email": email,
        "password": "Password123!",
    }
    r = client.post("/api/v1/auth/seeker/register", json=reg_payload)
    assert r.status_code == 201
    assert r.json()["success"] is True

    # 2. Verify Email
    v_payload = {"email": email, "code": "123456"}
    v_res = client.post("/api/v1/auth/seeker/verify-email", json=v_payload)
    assert v_res.status_code == 200
    assert v_res.json()["success"] is True

    # 3. Login Seeker
    l_payload = {"email": email, "password": "Password123!"}
    l_res = client.post("/api/v1/auth/seeker/login", json=l_payload)
    assert l_res.status_code == 200
    data = l_res.json()
    assert "access_token" in data
    assert data["role"] == "Job Seeker"
    assert data["email"] == email


def test_company_registration_and_2fa_login(client):
    work_email = "founder@newstartup.vn"
    # 1. Register Company
    reg_payload = {
        "company_name": "New Startup Vietnam",
        "contact_name": "Nguyen Founder",
        "email": work_email,
        "password": "Password123!",
        "industry": "Technology",
        "size": "1-10",
        "reg_number": "0399112233",
        "website": "https://newstartup.vn",
    }
    r = client.post("/api/v1/auth/company/register", json=reg_payload)
    assert r.status_code == 201
    assert r.json()["success"] is True

    # 2. Verify Work Email
    v_res = client.post("/api/v1/auth/company/verify-email", json={"email": work_email, "code": "123456"})
    assert v_res.status_code == 200

    # 3. Attempt Login before approval -> Expect PENDING_APPROVAL
    l_res = client.post("/api/v1/auth/company/login/initiate", json={"email": work_email, "password": "Password123!"})
    assert l_res.status_code == 200
    assert l_res.json()["status"] == "PENDING_APPROVAL"

    # 4. Super Admin Approves Company
    admin_login = client.post("/api/v1/auth/admin/login", json={"email": "admin@lamviec360.vn", "password": "password123"})
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Find the company id
    tenants = client.get("/api/v1/admin/tenants?status=Pending", headers=admin_headers).json()
    created_tenant = next((t for t in tenants if t["name"] == "New Startup Vietnam"), None)
    assert created_tenant is not None

    approve_res = client.post(f"/api/v1/admin/tenants/{created_tenant['id']}/approve", headers=admin_headers)
    assert approve_res.status_code == 200

    # 5. Initiate Login after approval -> Expect 2FA_REQUIRED with session_token
    init_res = client.post("/api/v1/auth/company/login/initiate", json={"email": work_email, "password": "Password123!"})
    assert init_res.status_code == 200
    init_data = init_res.json()
    assert init_data["status"] == "2FA_REQUIRED"
    assert "session_token" in init_data

    # 6. Verify 2FA OTP -> Issues Company Workspace JWT
    otp_res = client.post(
        "/api/v1/auth/company/login/verify-otp",
        json={"session_token": init_data["session_token"], "code": "123456"},
    )
    assert otp_res.status_code == 200
    token_data = otp_res.json()
    assert "access_token" in token_data
    assert token_data["role"] == "Company Admin"
    assert token_data["company_name"] == "New Startup Vietnam"


def test_super_admin_login_isolation(client):
    # 1. Super Admin login with correct credentials
    r = client.post("/api/v1/auth/admin/login", json={"email": "admin@lamviec360.vn", "password": "password123"})
    assert r.status_code == 200
    assert r.json()["role"] == "Super Admin"

    # 2. Seeker credentials on admin endpoint -> Rejected
    r2 = client.post("/api/v1/auth/admin/login", json={"email": "minh.tran@example.com", "password": "password123"})
    assert r2.status_code == 403
    assert "Super Admin" in r2.json()["detail"]
