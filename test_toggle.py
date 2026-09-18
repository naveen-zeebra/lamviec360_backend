import requests

# get a seeker token
resp = requests.post("http://localhost:8000/api/v1/auth/login", json={
    "email": "seeker@example.com",
    "password": "password123"
})
print("Login:", resp.status_code, resp.text)
if resp.status_code == 200:
    token = resp.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Toggle saved job
    res2 = requests.post("http://localhost:8000/api/v1/seeker/saved-jobs/11/toggle", headers=headers)
    print("Toggle:", res2.status_code, res2.text)
