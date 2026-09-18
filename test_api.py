import urllib.request
import json
import urllib.error

# 1. Login
data = json.dumps({"email": "seeker@example.com", "password": "password123"}).encode('utf-8')
req = urllib.request.Request("http://localhost:8000/api/v1/auth/seeker/login", data=data, headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req) as response:
        resp_data = json.loads(response.read().decode('utf-8'))
        token = resp_data.get('access_token')
        print("Login Success, Token:", token[:10] + "...")
        
        # 2. Toggle job
        req2 = urllib.request.Request("http://localhost:8000/api/v1/seeker/saved-jobs/11/toggle", data=b'', headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(req2) as res2:
            print("Toggle Success:", res2.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code, e.read().decode('utf-8'))
except Exception as e:
    print("Error:", e)
