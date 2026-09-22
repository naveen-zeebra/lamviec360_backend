import sys
from pathlib import Path
import uvicorn

# Add root directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared.environment import env

if __name__ == "__main__":
    print(f"Starting Company Gateway on http://{env.COMPANY_SERVICE_HOST}:{env.COMPANY_SERVICE_PORT}")
    print(f"Swagger Docs: http://localhost:{env.COMPANY_SERVICE_PORT}/docs")
    uvicorn.run(
        "services.company_service.app.main:app",
        host=env.COMPANY_SERVICE_HOST,
        port=env.COMPANY_SERVICE_PORT,
        reload=True,
    )
