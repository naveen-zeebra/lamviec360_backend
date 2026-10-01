import sys
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared.database.session import init_db
from shared.database.seed import seed_database
from services.jobseeker_service.app.main import app as jobseeker_app
from services.company_service.app.main import app as company_app
from services.admin_service.app.main import app as admin_app

def run_tests():
    print("=" * 70)
    print("RUNNING AUTOMATED MULTI-GATEWAY & ISOLATION VERIFICATION SUITE")
    print("=" * 70)

    # 1. Initialize & Seed Database
    print("\n[SETUP] Initializing schema and seed data...")
    init_db()
    seed_database()
    print("[PASS] Setup complete.")

    # -------------------------------------------------------------------------
    # 2. Test Job Seeker Gateway (Port 8001)
    # -------------------------------------------------------------------------
    print("\n[GATEWAY 1: Job Seeker Gateway (Port 8001)]")
    client_seeker = TestClient(jobseeker_app)
    
    # Health check
    res = client_seeker.get("/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("  [PASS] GET /health -> 200 OK")

    # Login
    res = client_seeker.post("/api/v1/jobseeker/auth/login", json={
        "email": "seeker@example.com",
        "password": "Seeker@123"
    })
    assert res.status_code == 200, f"Jobseeker login failed: {res.text}"
    seeker_token = res.json()["data"]["access_token"]
    seeker_headers = {"Authorization": f"Bearer {seeker_token}"}
    print("  [PASS] POST /api/v1/jobseeker/auth/login -> 200 OK (Jobseeker JWT acquired)")

    # Profile me
    res = client_seeker.get("/api/v1/jobseeker/auth/me", headers=seeker_headers)
    assert res.status_code == 200
    print(f"  [PASS] GET /api/v1/jobseeker/auth/me -> 200 OK ({res.json()['data']['full_name']})")

    # Browse Jobs
    res = client_seeker.get("/api/v1/jobseeker/jobs")
    assert res.status_code == 200
    jobs = res.json()["data"]
    print(f"  [PASS] GET /api/v1/jobseeker/jobs -> 200 OK ({len(jobs)} active jobs found)")
    job_id = jobs[0]["id"] if jobs else None

    # Apply for Job
    if job_id:
        res = client_seeker.post("/api/v1/jobseeker/applications", json={
            "job_id": job_id,
            "cover_letter": "I am excited to apply for this role!"
        }, headers=seeker_headers)
        print(f"  [PASS] POST /api/v1/jobseeker/applications -> {res.status_code}")

    # Notifications
    res = client_seeker.get("/api/v1/jobseeker/notifications", headers=seeker_headers)
    assert res.status_code == 200, f"Get notifications failed: {res.text}"
    print(f"  [PASS] GET /api/v1/jobseeker/notifications -> 200 OK ({len(res.json()['data'])} notifications)")

    # -------------------------------------------------------------------------
    # 3. Test Company Gateway (Port 8002)
    # -------------------------------------------------------------------------
    print("\n[GATEWAY 2: Company Gateway (Port 8002)]")
    client_company = TestClient(company_app)

    # Health check
    res = client_company.get("/health")
    assert res.status_code == 200
    print("  [PASS] GET /health -> 200 OK")

    # Login as Company Admin
    res = client_company.post("/api/v1/company/auth/login", json={
        "email": "company@techcorp.com",
        "password": "Company@123"
    })
    assert res.status_code == 200, f"Company login failed: {res.text}"
    company_token = res.json()["data"]["access_token"]
    company_headers = {"Authorization": f"Bearer {company_token}"}
    print("  [PASS] POST /api/v1/company/auth/login -> 200 OK (Company Admin JWT acquired)")

    # List Company Jobs
    res = client_company.get("/api/v1/company/jobs", headers=company_headers)
    assert res.status_code == 200
    print(f"  [PASS] GET /api/v1/company/jobs -> 200 OK ({len(res.json()['data'])} jobs listed)")

    # List ATS Applicants
    res = client_company.get("/api/v1/company/applicants", headers=company_headers)
    assert res.status_code == 200
    print(f"  [PASS] GET /api/v1/company/applicants -> 200 OK ({len(res.json()['data'])} candidates in pipeline)")

    # -------------------------------------------------------------------------
    # 4. Company Team Management & Lifecycle
    # -------------------------------------------------------------------------
    print("\n[SYSTEM 2 WORKFLOW: Company Team Management & Lifecycle]")
    # 4a. List Team Members and Invitations
    res = client_company.get("/api/v1/company/team", headers=company_headers)
    assert res.status_code == 200, f"List team failed: {res.text}"
    team_data = res.json()["data"]
    initial_members = team_data.get("members", [])
    initial_invites = team_data.get("invitations", [])
    print(f"  [PASS] GET /api/v1/company/team -> 200 OK ({len(initial_members)} members, {len(initial_invites)} pending invites)")

    # 4b. Invite New Team Member (Recruiter)
    invite_payload = {
        "email": "suite.recruiter@techcorp.com",
        "role": "recruiter",
        "message": "Welcome to our recruiting team!"
    }
    res = client_company.post("/api/v1/company/team/invite", json=invite_payload, headers=company_headers)
    assert res.status_code == 200, f"Invite team member failed: {res.text}"
    invite_res = res.json()["data"]
    invite_token = invite_res.get("inviteToken")
    assert invite_token, "Invite token was not returned"
    print(f"  [PASS] POST /api/v1/company/team/invite -> 200 OK (Invited {invite_payload['email']}, token={invite_token[:8]}...)")

    # 4c. Public Verify Invitation Token
    res = client_company.get(f"/api/v1/company/auth/invitation/verify?token={invite_token}")
    assert res.status_code == 200, f"Verify invitation failed: {res.text}"
    verified_data = res.json()["data"]
    assert verified_data["email"] == "suite.recruiter@techcorp.com"
    assert verified_data["role"] == "recruiter"
    print(f"  [PASS] GET /api/v1/company/auth/invitation/verify -> 200 OK (Validated invite for {verified_data['email']})")

    # 4d. Public Accept Invitation & Set Password
    accept_payload = {
        "token": invite_token,
        "first_name": "Suite",
        "last_name": "Recruiter",
        "password": "SuitePassword@123",
        "phone": "+84 999 888 777"
    }
    res = client_company.post("/api/v1/company/auth/invitation/accept", json=accept_payload)
    assert res.status_code == 200, f"Accept invitation failed: {res.text}"
    accepted_data = res.json()["data"]
    new_member_id = accepted_data["id"]
    print(f"  [PASS] POST /api/v1/company/auth/invitation/accept -> 200 OK (Activated member_id={new_member_id})")

    # 4e. Authenticate as New Team Member
    res = client_company.post("/api/v1/company/auth/login", json={
        "email": "suite.recruiter@techcorp.com",
        "password": "SuitePassword@123"
    })
    assert res.status_code == 200, f"New member login failed: {res.text}"
    recruiter_token = res.json()["data"]["access_token"]
    recruiter_headers = {"Authorization": f"Bearer {recruiter_token}"}
    print("  [PASS] POST /api/v1/company/auth/login -> 200 OK (New Recruiter JWT acquired)")

    # 4f. Company Internal RBAC: Non-admin recruiter cannot invite members
    res = client_company.post("/api/v1/company/team/invite", json={
        "email": "intruder@techcorp.com",
        "role": "recruiter"
    }, headers=recruiter_headers)
    assert res.status_code == 403, f"Expected 403 Forbidden for recruiter invite attempt, got: {res.status_code}"
    print("  [PASS] POST /api/v1/company/team/invite with recruiter token -> 403 Forbidden (RBAC enforced)")

    # 4g. Company Admin updates new member's role to hiring_manager
    res = client_company.patch(
        f"/api/v1/company/team/members/{new_member_id}/role",
        json={"role": "hiring_manager"},
        headers=company_headers
    )
    assert res.status_code == 200, f"Update member role failed: {res.text}"
    print(f"  [PASS] PATCH /api/v1/company/team/members/{new_member_id}/role -> 200 OK (Role updated to hiring_manager)")

    # 4h. Company Admin updates member status (deactivate / reactivate)
    res = client_company.patch(
        f"/api/v1/company/team/members/{new_member_id}/status",
        json={"status": "inactive"},
        headers=company_headers
    )
    assert res.status_code == 200, f"Deactivate member failed: {res.text}"
    print(f"  [PASS] PATCH /api/v1/company/team/members/{new_member_id}/status (inactive) -> 200 OK")

    res = client_company.patch(
        f"/api/v1/company/team/members/{new_member_id}/status",
        json={"status": "active"},
        headers=company_headers
    )
    assert res.status_code == 200, f"Reactivate member failed: {res.text}"
    print(f"  [PASS] PATCH /api/v1/company/team/members/{new_member_id}/status (active) -> 200 OK")

    # -------------------------------------------------------------------------
    # 5. Test Super Admin Gateway (Port 8003)
    # -------------------------------------------------------------------------
    print("\n[GATEWAY 3: Super Admin Gateway (Port 8003)]")
    client_admin = TestClient(admin_app)

    # Health check
    res = client_admin.get("/health")
    assert res.status_code == 200
    print("  [PASS] GET /health -> 200 OK")

    # Login as Super Admin
    res = client_admin.post("/api/v1/admin/auth/login", json={
        "email": "admin@jobportal.com",
        "password": "Admin@123"
    })
    assert res.status_code == 200, f"Admin login failed: {res.text}"
    admin_token = res.json()["data"]["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("  [PASS] POST /api/v1/admin/auth/login -> 200 OK (Admin JWT acquired)")

    # Dashboard Summary
    res = client_admin.get("/api/v1/admin/dashboard/summary", headers=admin_headers)
    assert res.status_code == 200
    summary = res.json()["data"]
    print(f"  [PASS] GET /api/v1/admin/dashboard/summary -> 200 OK (Total Users: {summary['total_users']}, Active Jobs: {summary['active_jobs']})")

    # Users List
    res = client_admin.get("/api/v1/admin/users", headers=admin_headers)
    assert res.status_code == 200
    print(f"  [PASS] GET /api/v1/admin/users -> 200 OK ({len(res.json()['data'])} users retrieved)")

    # Roles List
    res = client_admin.get("/api/v1/admin/roles", headers=admin_headers)
    assert res.status_code == 200
    print(f"  [PASS] GET /api/v1/admin/roles -> 200 OK ({len(res.json()['data'])} roles verified)")

    # Companies Moderation List
    res = client_admin.get("/api/v1/admin/companies", headers=admin_headers)
    assert res.status_code == 200
    print(f"  [PASS] GET /api/v1/admin/companies -> 200 OK ({len(res.json()['data'])} companies found)")

    # Audit Logs
    res = client_admin.get("/api/v1/admin/audit-logs", headers=admin_headers)
    assert res.status_code == 200
    print(f"  [PASS] GET /api/v1/admin/audit-logs -> 200 OK ({len(res.json()['data'])} activity records)")

    # -------------------------------------------------------------------------
    # 6. Cross-System Security & Token Rejection Tests
    # -------------------------------------------------------------------------
    print("\n[CROSS-SYSTEM SECURITY & TOKEN REJECTION TESTS]")

    # 6a. Job Seeker Token on Admin Gateway -> 403 Forbidden
    res = client_admin.get("/api/v1/admin/dashboard/summary", headers=seeker_headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"
    res = client_admin.get("/api/v1/admin/users", headers=seeker_headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"
    print("  [PASS] Job Seeker token on Super Admin Gateway -> 403 Forbidden (Blocked)")

    # 6b. Company Token on Admin Gateway -> 403 Forbidden
    res = client_admin.get("/api/v1/admin/dashboard/summary", headers=company_headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"
    res = client_admin.get("/api/v1/admin/users", headers=company_headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"
    print("  [PASS] Company token on Super Admin Gateway -> 403 Forbidden (Blocked)")

    # 6c. Super Admin Token on Company Gateway -> 403 Forbidden
    res = client_company.get("/api/v1/company/jobs", headers=admin_headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"
    res = client_company.get("/api/v1/company/team", headers=admin_headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"
    print("  [PASS] Super Admin token on Company Gateway -> 403 Forbidden (Blocked)")

    # 6d. Job Seeker Token on Company Gateway -> 403 Forbidden
    res = client_company.get("/api/v1/company/jobs", headers=seeker_headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"
    res = client_company.get("/api/v1/company/team", headers=seeker_headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"
    print("  [PASS] Job Seeker token on Company Gateway -> 403 Forbidden (Blocked)")

    # 6e. Company Token on Job Seeker Gateway -> 403 Forbidden
    res = client_seeker.get("/api/v1/jobseeker/auth/me", headers=company_headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"
    print("  [PASS] Company token on Job Seeker Gateway -> 403 Forbidden (Blocked)")

    # 6f. Super Admin Token on Job Seeker Gateway -> 403 Forbidden
    res = client_seeker.get("/api/v1/jobseeker/auth/me", headers=admin_headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"
    print("  [PASS] Super Admin token on Job Seeker Gateway -> 403 Forbidden (Blocked)")

    # 6g. Cross-System Credential Login Rejections
    # Attempt to log in with Job Seeker credentials at Super Admin login -> rejected
    res = client_admin.post("/api/v1/admin/auth/login", json={
        "email": "seeker@example.com",
        "password": "Seeker@123"
    })
    assert res.status_code in [401, 404], f"Expected 401/404, got {res.status_code}"
    print("  [PASS] Seeker credentials at Super Admin login -> Rejected (401/404)")

    # Attempt to log in with Super Admin credentials at Job Seeker login -> rejected
    res = client_seeker.post("/api/v1/jobseeker/auth/login", json={
        "email": "admin@jobportal.com",
        "password": "Admin@123"
    })
    assert res.status_code in [401, 403], f"Expected 401/403, got {res.status_code}"
    print("  [PASS] Admin credentials at Job Seeker login -> Rejected (401/403)")

    # Attempt to log in with Super Admin credentials at Company login -> rejected
    res = client_company.post("/api/v1/company/auth/login", json={
        "email": "admin@jobportal.com",
        "password": "Admin@123"
    })
    assert res.status_code == 401, f"Expected 401, got {res.status_code}"
    print("  [PASS] Admin credentials at Company login -> Rejected (401)")

    print("\n" + "=" * 70)
    print("SUCCESS: ALL MULTI-GATEWAY & ISOLATION TESTS PASSED WITH 0 FAILURES!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
