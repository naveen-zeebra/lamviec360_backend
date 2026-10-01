import sys
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared.database.session import init_db
from shared.database.seed import seed_database
from services.jobseeker_service.app.main import app as jobseeker_app
from services.company_service.app.main import app as company_app
from services.admin_service.app.main import app as admin_app

def run_integration_tests():
    print("=" * 75)
    print("END-TO-END ALL APIS INTEGRATION TEST ACROSS ALL 3 WEB FRONTENDS")
    print("=" * 75)

    # Database setup
    init_db()
    seed_database()
    print("[INIT] Database initialized and seeded successfully.\n")

    passed_count = 0
    total_count = 0

    def assert_test(condition, label, details=""):
        nonlocal passed_count, total_count
        total_count += 1
        if condition:
            passed_count += 1
            print(f"  [PASS] {label} {details}")
        else:
            print(f"  [FAIL] {label} {details}")
            raise AssertionError(f"Test failed: {label} {details}")

    # =========================================================================
    # FRONTEND 1: new-super-admin-web (Target: Port 8003 / Super Admin Gateway)
    # =========================================================================
    print("-" * 75)
    print("FRONTEND 1: new-super-admin-web (Super Admin Portal - Port 8003)")
    print("-" * 75)
    client_admin = TestClient(admin_app)

    # 1.1 adminApi.auth.login
    res = client_admin.post("/api/v1/auth/login", json={
        "email": "admin@jobportal.com",
        "password": "Admin@123"
    })
    assert_test(res.status_code == 200, "adminApi.auth.login (POST /api/v1/auth/login)", f"-> 200 OK")
    admin_token = res.json()["data"]["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1.2 adminApi.auth.getMe
    res = client_admin.get("/api/v1/profile/me", headers=admin_headers)
    assert_test(res.status_code == 200, "adminApi.auth.getMe (GET /api/v1/profile/me)", f"-> 200 OK (Email: {res.json()['data']['email']})")

    # 1.3 adminApi.auth.updateProfile
    res = client_admin.put("/api/v1/profile/me", json={
        "first_name": "Super",
        "last_name": "Admin",
        "phone": "+84 900 123 456"
    }, headers=admin_headers)
    assert_test(res.status_code == 200, "adminApi.auth.updateProfile (PUT /api/v1/profile/me)", f"-> 200 OK")

    # 1.4 adminApi.dashboard.getSummary
    res = client_admin.get("/api/v1/dashboard/summary", headers=admin_headers)
    assert_test(res.status_code == 200, "adminApi.dashboard.getSummary (GET /api/v1/dashboard/summary)", f"-> 200 OK")

    # 1.5 adminApi.dashboard.getGrowth
    res = client_admin.get("/api/v1/dashboard/growth", headers=admin_headers)
    assert_test(res.status_code == 200, "adminApi.dashboard.getGrowth (GET /api/v1/dashboard/growth)", f"-> 200 OK")

    # 1.6 adminApi.dashboard.getActivities
    res = client_admin.get("/api/v1/dashboard/activities", headers=admin_headers)
    assert_test(res.status_code == 200, "adminApi.dashboard.getActivities (GET /api/v1/dashboard/activities)", f"-> 200 OK")

    # 1.7 adminApi.companies.list
    res = client_admin.get("/api/v1/companies", headers=admin_headers)
    assert_test(res.status_code == 200, "adminApi.companies.list (GET /api/v1/companies)", f"-> 200 OK ({len(res.json()['data'])} companies)")
    company_id = res.json()["data"][0]["id"] if res.json()["data"] else 1

    # 1.8 adminApi.companies.get
    res = client_admin.get(f"/api/v1/companies/{company_id}", headers=admin_headers)
    assert_test(res.status_code == 200, f"adminApi.companies.get (GET /api/v1/companies/{company_id})", f"-> 200 OK")

    # 1.9 adminApi.companies.verify
    res = client_admin.patch(f"/api/v1/companies/{company_id}/verify", json={
        "verification_status": "verified",
        "verification_notes": "All legal documents verified."
    }, headers=admin_headers)
    assert_test(res.status_code == 200, f"adminApi.companies.verify (PATCH /api/v1/companies/{company_id}/verify)", f"-> 200 OK")

    # 1.10 adminApi.companies.toggleFeature
    res = client_admin.patch(f"/api/v1/companies/{company_id}/feature", headers=admin_headers)
    assert_test(res.status_code == 200, f"adminApi.companies.toggleFeature (PATCH /api/v1/companies/{company_id}/feature)", f"-> 200 OK")

    # 1.11 adminApi.users.list & stats
    res = client_admin.get("/api/v1/users", headers=admin_headers)
    assert_test(res.status_code == 200, "adminApi.users.list (GET /api/v1/users)", f"-> 200 OK ({len(res.json()['data'])} users)")

    res = client_admin.get("/api/v1/users/stats", headers=admin_headers)
    assert_test(res.status_code == 200, "adminApi.users.getStats (GET /api/v1/users/stats)", f"-> 200 OK")

    # 1.12 adminApi.jobs.list & moderation
    res = client_admin.get("/api/v1/jobs", headers=admin_headers)
    assert_test(res.status_code == 200, "adminApi.jobs.list (GET /api/v1/jobs)", f"-> 200 OK ({len(res.json()['data'])} jobs in moderation)")
    admin_job_id = res.json()["data"][0]["id"]

    res = client_admin.get(f"/api/v1/jobs/{admin_job_id}/reports", headers=admin_headers)
    assert_test(res.status_code == 200, f"adminApi.jobs.getReports (GET /api/v1/jobs/{admin_job_id}/reports)", f"-> 200 OK")

    res = client_admin.patch(f"/api/v1/jobs/{admin_job_id}/moderate", json={
        "moderation_status": "approved",
        "moderation_notes": "Reviewed and cleared by super admin"
    }, headers=admin_headers)
    assert_test(res.status_code == 200, f"adminApi.jobs.moderate (PATCH /api/v1/jobs/{admin_job_id}/moderate)", f"-> 200 OK (Moderated to approved)")

    # 1.13 adminApi.adminUsers.list & roles
    res = client_admin.get("/api/v1/admin-users", headers=admin_headers)
    assert_test(res.status_code == 200, "adminApi.adminUsers.list (GET /api/v1/admin-users)", f"-> 200 OK ({len(res.json()['data'])} platform admins)")

    res = client_admin.get("/api/v1/admin-users/roles", headers=admin_headers)
    assert_test(res.status_code == 200, "adminApi.adminUsers.getRoles (GET /api/v1/admin-users/roles)", f"-> 200 OK ({len(res.json()['data'])} admin roles)")

    # 1.14 adminApi.roles.list
    res = client_admin.get("/api/v1/roles", headers=admin_headers)
    assert_test(res.status_code == 200, "adminApi.roles.list (GET /api/v1/roles)", f"-> 200 OK ({len(res.json()['data'])} RBAC roles)")

    # 1.15 adminApi.plans.list
    res = client_admin.get("/api/v1/plans", headers=admin_headers)
    assert_test(res.status_code == 200, "adminApi.plans.list (GET /api/v1/plans)", f"-> 200 OK ({len(res.json()['data'])} commercial plans)")

    # 1.16 adminApi.auditLogs.list
    res = client_admin.get("/api/v1/audit-logs", headers=admin_headers)
    assert_test(res.status_code == 200, "adminApi.auditLogs.list (GET /api/v1/audit-logs)", f"-> 200 OK ({len(res.json()['data'])} audit events)")


    # =========================================================================
    # FRONTEND 2: lamviec360_company_web (Target: Port 8002 / Company Gateway)
    # =========================================================================
    print("\n" + "-" * 75)
    print("FRONTEND 2: lamviec360_company_web (Employer / Company Portal - Port 8002)")
    print("-" * 75)
    client_company = TestClient(company_app)

    # 2.1 Standard Direct Login
    res = client_company.post("/api/v1/company/auth/login", json={
        "email": "company@techcorp.com",
        "password": "Company@123"
    })
    assert_test(res.status_code == 200, "companyAuth.standardCompanyLogin (POST /auth/login)", f"-> 200 OK")
    company_token = res.json()["data"]["access_token"]
    company_headers = {"Authorization": f"Bearer {company_token}"}

    # 2.2 2FA Initiate & Verify OTP Login
    res = client_company.post("/api/v1/company/auth/login/initiate", json={
        "email": "company@techcorp.com",
        "password": "Company@123"
    })
    assert_test(res.status_code == 200, "companyAuth.initiateCompanyLogin (POST /auth/login/initiate)", f"-> 200 OK")
    session_token = res.json()["data"]["session_token"]

    res = client_company.post("/api/v1/company/auth/login/verify-otp", json={
        "session_token": session_token,
        "code": "123456"
    })
    assert_test(res.status_code == 200, "companyAuth.verifyCompanyOtp (POST /auth/login/verify-otp)", f"-> 200 OK (OTP Verified)")

    # 2.3 companyAuth.getCompanyMe
    res = client_company.get("/api/v1/company/auth/me", headers=company_headers)
    assert_test(res.status_code == 200, "companyAuth.getCompanyMe (GET /auth/me)", f"-> 200 OK ({res.json()['data']['company_name']})")

    # 2.4 companyApi.getCompanyProfile & updateCompanyProfile
    res = client_company.get("/api/v1/company/profile", headers=company_headers)
    assert_test(res.status_code == 200, "companyApi.getCompanyProfile (GET /profile)", f"-> 200 OK")

    res = client_company.put("/api/v1/company/profile", json={
        "company_name": "TechCorp Global",
        "website": "https://techcorp.example.com",
        "industry": "Software & IT",
        "company_size": "201-500 employees"
    }, headers=company_headers)
    assert_test(res.status_code == 200, "companyApi.updateCompanyProfile (PUT /profile)", f"-> 200 OK")

    # 2.5 companyApi.getCompanyDashboard
    res = client_company.get("/api/v1/company/dashboard", headers=company_headers)
    assert_test(res.status_code == 200, "companyApi.getCompanyDashboard (GET /dashboard)", f"-> 200 OK")

    # 2.6 companyApi.listCompanyJobs
    res = client_company.get("/api/v1/company/jobs", headers=company_headers)
    assert_test(res.status_code == 200, "companyApi.listCompanyJobs (GET /jobs)", f"-> 200 OK ({len(res.json()['data'])} jobs)")

    # 2.7 companyApi.createCompanyJob
    res = client_company.post("/api/v1/company/jobs", json={
        "title": "Staff Platform Architect",
        "description": "Lead enterprise cloud systems design and mentor staff engineers.",
        "requirements": "7+ years distributed systems, Python, Kubernetes.",
        "benefits": "Competitive compensation, equity, healthcare.",
        "job_type": "Full-time",
        "workplace_type": "Hybrid",
        "experience_level": "Lead",
        "city": "Ho Chi Minh City",
        "country": "Vietnam",
        "salary_min": 45000000.0,
        "salary_max": 75000000.0,
        "salary_currency": "VND",
        "required_skills": "Python, Kubernetes, FastAPI, PostgreSQL",
    }, headers=company_headers)
    assert_test(res.status_code == 200, "companyApi.createCompanyJob (POST /jobs)", f"-> 200 OK")
    created_job_id = res.json()["data"]["id"]

    # 2.8 companyApi.getCompanyJobDetail & update
    res = client_company.get(f"/api/v1/company/jobs/{created_job_id}", headers=company_headers)
    assert_test(res.status_code == 200, f"companyApi.getCompanyJobDetail (GET /jobs/{created_job_id})", f"-> 200 OK")

    res = client_company.put(f"/api/v1/company/jobs/{created_job_id}", json={
        "title": "Principal Platform Architect",
    }, headers=company_headers)
    assert_test(res.status_code == 200, f"companyApi.updateCompanyJob (PUT /jobs/{created_job_id})", f"-> 200 OK")

    # 2.9 companyApi.setCompanyJobStatus (toggle)
    res = client_company.patch(f"/api/v1/company/jobs/{created_job_id}/status?status=paused", headers=company_headers)
    assert_test(res.status_code == 200, "companyApi.setCompanyJobStatus (PATCH /jobs/{id}/status)", f"-> 200 OK")

    # 2.10 companyApi.duplicateCompanyJob
    res = client_company.post(f"/api/v1/company/jobs/{created_job_id}/duplicate", headers=company_headers)
    assert_test(res.status_code == 200, "companyApi.duplicateCompanyJob (POST /jobs/{id}/duplicate)", f"-> 200 OK")

    # 2.11 companyApi.listCompanyCandidates & stage counts
    res = client_company.get("/api/v1/company/applicants", headers=company_headers)
    assert_test(res.status_code == 200, "companyApi.listCompanyCandidates (GET /applicants)", f"-> 200 OK ({len(res.json()['data'])} candidates)")
    cand_id = res.json()["data"][0]["id"] if res.json()["data"] else None

    res = client_company.get("/api/v1/company/applicants/stage-counts", headers=company_headers)
    assert_test(res.status_code == 200, "companyApi.getCompanyCandidateCounts (GET /applicants/stage-counts)", f"-> 200 OK")

    # 2.12 Candidate notes & status updates
    if cand_id:
        res = client_company.post(f"/api/v1/company/applicants/{cand_id}/notes", json={
            "text": "Strong technical screen performance."
        }, headers=company_headers)
        assert_test(res.status_code == 200, f"companyApi.addCandidateNote (POST /applicants/{cand_id}/notes)", f"-> 200 OK")

        res = client_company.patch(f"/api/v1/company/applicants/{cand_id}/status", json={
            "status": "interviewing",
            "rating": 5
        }, headers=company_headers)
        assert_test(res.status_code == 200, f"companyApi.updateCandidateStage (PATCH /applicants/{cand_id}/status)", f"-> 200 OK")

    # 2.13 companyApi.getCompanyTeam & inviteTeamMember
    res = client_company.get("/api/v1/company/team", headers=company_headers)
    assert_test(res.status_code == 200, "companyApi.getCompanyTeam (GET /team)", f"-> 200 OK")

    res = client_company.post("/api/v1/company/team/invite", json={
        "email": "frontend.integrator@techcorp.com",
        "role": "recruiter",
        "message": "Welcome to our team"
    }, headers=company_headers)
    assert_test(res.status_code == 200, "companyApi.inviteTeamMember (POST /team/invite)", f"-> 200 OK")
    invite_token = res.json()["data"]["inviteToken"]

    # 2.14 Invitation verification (supports both /auth/invitation/verify and /auth/invite/{token})
    res = client_company.get(f"/api/v1/company/auth/invitation/verify?token={invite_token}")
    assert_test(res.status_code == 200, "companyAuth.getInvitationByToken (GET /auth/invitation/verify)", f"-> 200 OK")

    res = client_company.get(f"/api/v1/company/auth/invite/{invite_token}")
    assert_test(res.status_code == 200, "companyAuth.getInvitationByToken legacy (GET /auth/invite/{token})", f"-> 200 OK")

    # 2.15 Employee activation (supports both /auth/invitation/accept and /auth/activate-invite)
    res = client_company.post("/api/v1/company/auth/activate-invite", json={
        "invite_token": invite_token,
        "name": "Frontend Integrator",
        "password": "Password@123"
    })
    assert_test(res.status_code == 200, "companyAuth.activateTeamInvitation (POST /auth/activate-invite)", f"-> 200 OK")

    # 2.16 companyApi.purgeCompanyData
    res = client_company.post("/api/v1/company/data-retention/purge?months=12", headers=company_headers)
    assert_test(res.status_code == 200, "companyApi.purgeCompanyData (POST /data-retention/purge)", f"-> 200 OK")


    # =========================================================================
    # FRONTEND 3: lamviec360_mockup_screen (Target: Port 8001 / Job Seeker Gateway)
    # =========================================================================
    print("\n" + "-" * 75)
    print("FRONTEND 3: lamviec360_mockup_screen (Job Seeker / Candidate Portal - Port 8001)")
    print("-" * 75)
    client_seeker = TestClient(jobseeker_app)

    # 3.1 publicApi.fetchPublicJobs
    res = client_seeker.get("/api/v1/jobseeker/jobs")
    assert_test(res.status_code == 200, "publicApi.fetchPublicJobs (GET /jobs)", f"-> 200 OK ({len(res.json()['data'])} jobs available)")
    first_job_id = res.json()["data"][0]["id"] if res.json()["data"] else None

    # 3.2 publicApi.fetchPublicJobDetail
    if first_job_id:
        res = client_seeker.get(f"/api/v1/jobseeker/jobs/{first_job_id}")
        assert_test(res.status_code == 200, f"publicApi.fetchPublicJobDetail (GET /jobs/{first_job_id})", f"-> 200 OK")

    # 3.3 seekerAuth.loginSeeker
    res = client_seeker.post("/api/v1/jobseeker/auth/login", json={
        "email": "seeker@example.com",
        "password": "Seeker@123"
    })
    assert_test(res.status_code == 200, "seekerAuth.loginSeeker (POST /auth/login)", f"-> 200 OK (JWT acquired)")
    seeker_token = res.json()["data"]["access_token"]
    seeker_headers = {"Authorization": f"Bearer {seeker_token}"}

    # 3.4 seekerAuth.getSeekerMe
    res = client_seeker.get("/api/v1/jobseeker/auth/me", headers=seeker_headers)
    assert_test(res.status_code == 200, "seekerAuth.getSeekerMe (GET /auth/me)", f"-> 200 OK (User: {res.json()['data']['full_name']})")

    # 3.5 seekerApi.getSeekerProfile & updateSeekerProfile
    res = client_seeker.get("/api/v1/jobseeker/profile", headers=seeker_headers)
    assert_test(res.status_code == 200, "seekerApi.getSeekerProfile (GET /profile)", f"-> 200 OK")

    res = client_seeker.put("/api/v1/jobseeker/profile", json={
        "headline": "Lead Full Stack & Systems Engineer",
        "skills": "Python, FastAPI, Next.js, TypeScript, PostgreSQL",
        "experience_years": 6.5,
        "city": "Ho Chi Minh City",
        "country": "Vietnam"
    }, headers=seeker_headers)
    assert_test(res.status_code == 200, "seekerApi.updateSeekerProfile (PUT /profile)", f"-> 200 OK")

    # 3.6 seekerApi.fetchSavedJobs, saveJob, unsaveJob
    if first_job_id:
        res = client_seeker.post(f"/api/v1/jobseeker/profile/saved-jobs/{first_job_id}", headers=seeker_headers)
        assert_test(res.status_code == 200, f"seekerApi.saveJob (POST /profile/saved-jobs/{first_job_id})", f"-> 200 OK")

        res = client_seeker.get("/api/v1/jobseeker/profile/saved-jobs", headers=seeker_headers)
        assert_test(res.status_code == 200, "seekerApi.fetchSavedJobs (GET /profile/saved-jobs)", f"-> 200 OK ({len(res.json()['data'])} saved jobs)")

        res = client_seeker.delete(f"/api/v1/jobseeker/profile/saved-jobs/{first_job_id}", headers=seeker_headers)
        assert_test(res.status_code == 200, f"seekerApi.unsaveJob (DELETE /profile/saved-jobs/{first_job_id})", f"-> 200 OK")

    # 3.7 seekerApi.fetchSeekerApplications
    res = client_seeker.get("/api/v1/jobseeker/applications", headers=seeker_headers)
    assert_test(res.status_code == 200, "seekerApi.fetchSeekerApplications (GET /applications)", f"-> 200 OK ({len(res.json()['data'])} applications)")

    # 3.8 publicApi.reportJob
    if first_job_id:
        res = client_seeker.post(f"/api/v1/jobseeker/jobs/{first_job_id}/report", json={
            "reason": "Inaccurate Salary",
            "details": "Listed salary does not match the actual offer communicated.",
            "reporter_name": "Nguyen Van A",
            "reporter_email": "seeker@example.com"
        })
        assert_test(res.status_code == 200, f"publicApi.reportJob (POST /jobs/{first_job_id}/report)", f"-> 200 OK (Report #{res.json()['data']['report_id']} filed)")

    print("\n" + "=" * 75)
    print(f"INTEGRATION TEST SUMMARY: {passed_count}/{total_count} API CALLS VERIFIED 100% OPERATIONAL")
    print("=" * 75)

if __name__ == "__main__":
    run_integration_tests()
