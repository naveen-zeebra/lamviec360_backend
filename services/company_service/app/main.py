import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Add repository root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from shared.environment import env
from shared.database.session import init_db
from shared.database.seed import seed_database
from shared.utils.rate_limiter import limiter
from shared.utils.logger import get_logger
from services.company_service.app.routes_manager import register_routes

logger = get_logger("company_service")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Company Gateway...")
    init_db()
    seed_database()
    logger.info("Company Gateway initialized successfully.")
    yield
    logger.info("Shutting down Company Gateway...")

app = FastAPI(
    title="Company Gateway API",
    description="Dedicated API Gateway for Employers & Recruiters: Company profile, job posting lifecycle, and ATS applicant tracking.",
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
        "service": "company_service",
        "port": env.COMPANY_SERVICE_PORT,
    }

@app.get("/", tags=["Root"])
def root():
    return {
        "service": "Company Gateway API",
        "version": "1.0.0",
        "documentation": "/docs",
        "api_prefix": "/api/v1/company",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "services.company_service.app.main:app",
        host=env.COMPANY_SERVICE_HOST,
        port=env.COMPANY_SERVICE_PORT,
        reload=True,
    )
