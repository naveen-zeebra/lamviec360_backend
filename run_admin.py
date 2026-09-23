import sys
from pathlib import Path
import uvicorn

# Add root directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared.environment import env

if __name__ == "__main__":
    print(f"Starting Super Admin Gateway on http://{env.ADMIN_SERVICE_HOST}:{env.ADMIN_SERVICE_PORT}")
    print(f"Swagger Docs: http://localhost:{env.ADMIN_SERVICE_PORT}/docs")
    root_dir = Path(__file__).resolve().parent
    uvicorn.run(
        "services.admin_service.app.main:app",
        host=env.ADMIN_SERVICE_HOST,
        port=env.ADMIN_SERVICE_PORT,
        reload=True,
        reload_dirs=[str(root_dir / "services"), str(root_dir / "shared")],
    )
