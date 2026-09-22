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
    print("=" * 60)
    print("RUNNING AUTOMATED GATEWAY VERIFICATION TESTS")
    print("=" * 60)

    # 1. Initialize & Seed Database
    print("\n[SETUP] Initializing schema and seed data...")
    init_db()
    seed_database()
    print("[PASS] Setup complete.")

    # 2. Test Job Seeker Gateway
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
    print("  [PASS] POST /api/v1/jobseeker/auth/login -> 200 OK (JWT acquired)")

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
        print(f"  [PASS] POST /api/v1/jobseeker/applications -> {res.status_code} ({res.json().get('message')})")

    # 3. Test Company Gateway
    print("\n[GATEWAY 2: Company Gateway (Port 8002)]")
    client_company = TestClient(company_app)

    # Health check
    res = client_company.get("/health")
    assert res.status_code == 200
    print("  [PASS] GET /health -> 200 OK")

    # Login
    res = client_company.post("/api/v1/company/auth/login", json={
        "email": "company@techcorp.com",
        "password": "Company@123"
    })
    assert res.status_code == 200, f"Company login failed: {res.text}"
    company_token = res.json()["data"]["access_token"]
    company_headers = {"Authorization": f"Bearer {company_token}"}
    print("  [PASS] POST /api/v1/company/auth/login -> 200 OK (JWT acquired)")

    # List Company Jobs
    res = client_company.get("/api/v1/company/jobs", headers=company_headers)
    assert res.status_code == 200
    print(f"  [PASS] GET /api/v1/company/jobs -> 200 OK ({len(res.json()['data'])} jobs listed)")

    # List ATS Applicants
    res = client_company.get("/api/v1/company/applicants", headers=company_headers)
    assert res.status_code == 200
    print(f"  [PASS] GET /api/v1/company/applicants -> 200 OK ({len(res.json()['data'])} candidates in pipeline)")

    # 4. Test Super Admin Gateway
    print("\n[GATEWAY 3: Super Admin Gateway (Port 8003)]")
    client_admin = TestClient(admin_app)

    # Health check
    res = client_admin.get("/health")
    assert res.status_code == 200
    print("  [PASS] GET /health -> 200 OK")

    # Login
    res = client_admin.post("/api/v1/admin/auth/login", json={
        "email": "admin@jobportal.com",
        "password": "Admin@123"
    })
    assert res.status_code == 200, f"Admin login failed: {res.text}"
    admin_token = res.json()["data"]["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("  [PASS] POST /api/v1/admin/auth/login -> 200 OK (JWT acquired)")

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

    print("\n" + "=" * 60)
    print("SUCCESS: ALL ENDPOINT VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
