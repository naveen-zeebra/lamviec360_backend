from fastapi.testclient import TestClient
from app.main import app

def test_job_lifecycle_and_candidate_pipeline(client):
    # 1. Company Admin Login (Lan Tran @ ABC Technologies)
    init_res = client.post("/api/v1/auth/company/login/initiate", json={"email": "lan.tran@abctech.vn", "password": "password123"})
    session_token = init_res.json()["session_token"]
    otp_res = client.post("/api/v1/auth/company/login/verify-otp", json={"session_token": session_token, "code": "123456"})
    emp_token = otp_res.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    # 2. Post a new Job as Company Admin
    job_payload = {
        "title": "Lead DevOps Engineer",
        "department": "Infrastructure",
        "type": "Full-time",
        "location": "Ho Chi Minh City",
        "salary_min": "35000000",
        "salary_max": "50000000",
        "negotiable": False,
        "jd": "Lead our cloud infrastructure and CI/CD pipelines.",
        "skills": ["Kubernetes", "Terraform", "AWS", "CI/CD"],
        "status": "Published",
    }
    create_job_res = client.post("/api/v1/company/jobs", json=job_payload, headers=emp_headers)
    assert create_job_res.status_code == 201
    job_data = create_job_res.json()
    job_id = job_data["id"]

    # 3. Public search finds the newly published job
    public_res = client.get(f"/api/v1/public/jobs?q=DevOps")
    assert public_res.status_code == 200
    jobs_found = public_res.json()
    assert any(j["id"] == job_id for j in jobs_found)

    # 4. Job Seeker Login (Minh Tran)
    seeker_login = client.post("/api/v1/auth/seeker/login", json={"email": "minh.tran@example.com", "password": "password123"})
    seeker_token = seeker_login.json()["access_token"]
    seeker_headers = {"Authorization": f"Bearer {seeker_token}"}

    # 5. Seeker applies to the new job
    apply_payload = {
        "job_id": job_id,
        "resume_file_name": "Minh_Tran_CV.pdf",
        "cover_letter": "I have extensive DevOps experience.",
    }
    apply_res = client.post(f"/api/v1/seeker/jobs/{job_id}/apply", json=apply_payload, headers=seeker_headers)
    assert apply_res.status_code == 200
    app_id = apply_res.json()["data"]["application_id"]

    # 6. Company Admin checks candidates list and advances candidate to Shortlisted
    candidates_res = client.get(f"/api/v1/company/candidates?job_id={job_id}", headers=emp_headers)
    assert candidates_res.status_code == 200
    candidates = candidates_res.json()
    assert any(c["id"] == app_id for c in candidates)

    stage_res = client.patch(
        f"/api/v1/company/candidates/{app_id}/stage",
        json={"stage": "Shortlisted"},
        headers=emp_headers,
    )
    assert stage_res.status_code == 200

    # 7. Seeker checks applications and sees updated status
    my_apps = client.get("/api/v1/seeker/applications", headers=seeker_headers).json()
    updated_app = next((a for a in my_apps if a["id"] == app_id), None)
    assert updated_app is not None
    assert updated_app["stage"] == "Shortlisted"
