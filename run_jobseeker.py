import sys
from pathlib import Path
import uvicorn

# Add root directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared.environment import env

if __name__ == "__main__":
    print(f"Starting Job Seeker Gateway on http://{env.JOBSEEKER_SERVICE_HOST}:{env.JOBSEEKER_SERVICE_PORT}")
    print(f"Swagger Docs: http://localhost:{env.JOBSEEKER_SERVICE_PORT}/docs")
    uvicorn.run(
        "services.jobseeker_service.app.main:app",
        host=env.JOBSEEKER_SERVICE_HOST,
        port=env.JOBSEEKER_SERVICE_PORT,
        reload=True,
    )
