import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Add repository root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from shared.environment import env
from shared.database.session import init_db
from shared.database.seed import seed_database
from shared.utils.rate_limiter import limiter
from shared.utils.logger import get_logger
from services.jobseeker_service.app.routes_manager import register_routes

logger = get_logger("jobseeker_service")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Job Seeker Gateway...")
    init_db()
    seed_database()
    logger.info("Job Seeker Gateway initialized successfully.")
    yield
    logger.info("Shutting down Job Seeker Gateway...")

app = FastAPI(
    title="Job Seeker Gateway API",
    description="Dedicated API Gateway for Job Seekers: Candidate registration, resume profile, job search, and application tracking.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# SlowAPI Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS Middleware
origins = env.CORS_ORIGINS if isinstance(env.CORS_ORIGINS, list) else [o.strip() for o in str(env.CORS_ORIGINS).split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
register_routes(app)

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "jobseeker_service",
        "port": env.JOBSEEKER_SERVICE_PORT,
    }

@app.get("/", tags=["Root"])
def root():
    return {
        "service": "Job Seeker Gateway API",
        "version": "1.0.0",
        "documentation": "/docs",
        "api_prefix": "/api/v1/jobseeker",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "services.jobseeker_service.app.main:app",
        host=env.JOBSEEKER_SERVICE_HOST,
        port=env.JOBSEEKER_SERVICE_PORT,
        reload=True,
    )
