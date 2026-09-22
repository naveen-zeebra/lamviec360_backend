import os
import sys
import time
import socket
import subprocess
import signal
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from shared.environment import env
from shared.database.session import init_db
from shared.database.seed import seed_database

SERVICES = [
    {
        "name": "Job Seeker Gateway",
        "port": env.JOBSEEKER_SERVICE_PORT,
        "script": "run_jobseeker.py",
        "url": f"http://localhost:{env.JOBSEEKER_SERVICE_PORT}/docs",
    },
    {
        "name": "Company Gateway",
        "port": env.COMPANY_SERVICE_PORT,
        "script": "run_company.py",
        "url": f"http://localhost:{env.COMPANY_SERVICE_PORT}/docs",
    },
    {
        "name": "Super Admin Gateway",
        "port": env.ADMIN_SERVICE_PORT,
        "script": "run_admin.py",
        "url": f"http://localhost:{env.ADMIN_SERVICE_PORT}/docs",
    },
]

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0

def print_banner():
    print("=" * 70)
    print("        MULTI-GATEWAY SERVER ORCHESTRATOR")
    print("=" * 70)
    for s in SERVICES:
        status_str = "[!] Port Busy" if is_port_in_use(s["port"]) else "[OK] Port Available"
        print(f"  * {s['name']:<22} Port: {s['port']:<6} {status_str:<20} -> {s['url']}")
    print("=" * 70)

def main():
    print_banner()

    # Step 1: Pre-initialize database schema and demo seeds
    print("[1/2] Initializing Shared Database & Default Seeds...")
    try:
        init_db()
        seed_database()
        print("      [OK] Database tables and default seeds verified.")
    except Exception as e:
        print(f"      [WARNING] Database initialization warning: {e}")

    # Step 2: Spawn all 3 gateway servers
    print("\n[2/2] Launching 3 Gateway Servers concurrently...")
    processes = []
    
    python_exe = sys.executable

    try:
        for s in SERVICES:
            script_path = str(BASE_DIR / s["script"])
            print(f"      Starting {s['name']} on port {s['port']}...")
            p = subprocess.Popen(
                [python_exe, script_path],
                cwd=str(BASE_DIR),
            )
            processes.append((s, p))

        print("\nAll 3 Gateway Services are running!")
        print("Press Ctrl+C to stop all servers.\n")

        # Keep parent alive while children are running
        while True:
            time.sleep(1)
            for s, p in processes:
                ret = p.poll()
                if ret is not None:
                    print(f"Service {s['name']} exited with code {ret}")

    except KeyboardInterrupt:
        print("\nStopping all services...")
    finally:
        for s, p in processes:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    p.kill()
        print("All services stopped.")

if __name__ == "__main__":
    main()
