from fastapi import FastAPI
from services.jobseeker_service.app.api.auth.router import router as auth_router
from services.jobseeker_service.app.api.profile.router import router as profile_router
from services.jobseeker_service.app.api.jobs.router import router as jobs_router
from services.jobseeker_service.app.api.applications.router import router as applications_router

PREFIX = "/api/v1/jobseeker"

def register_routes(app: FastAPI) -> None:
    app.include_router(auth_router, prefix=PREFIX)
    app.include_router(profile_router, prefix=PREFIX)
    app.include_router(jobs_router, prefix=PREFIX)
    app.include_router(applications_router, prefix=PREFIX)
