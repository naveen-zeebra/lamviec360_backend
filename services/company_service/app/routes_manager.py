from fastapi import FastAPI
from services.company_service.app.api.auth.router import router as auth_router
from services.company_service.app.api.profile.router import router as profile_router
from services.company_service.app.api.jobs.router import router as jobs_router
from services.company_service.app.api.applicants.router import router as applicants_router
from services.company_service.app.api.dashboard.router import router as dashboard_router
from services.company_service.app.api.team.router import router as team_router
from services.company_service.app.api.data_retention.router import router as data_retention_router

PREFIX = "/api/v1/company"

def register_routes(app: FastAPI) -> None:
    app.include_router(auth_router, prefix=PREFIX)
    app.include_router(profile_router, prefix=PREFIX)
    app.include_router(jobs_router, prefix=PREFIX)
    app.include_router(applicants_router, prefix=PREFIX)
    app.include_router(dashboard_router, prefix=PREFIX)
    app.include_router(team_router, prefix=PREFIX)
    app.include_router(data_retention_router, prefix=PREFIX)
