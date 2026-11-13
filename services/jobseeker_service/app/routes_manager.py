from fastapi import FastAPI
from services.jobseeker_service.app.api.auth.router import router as auth_router
from services.jobseeker_service.app.api.profile.router import router as profile_router
from services.jobseeker_service.app.api.jobs.router import router as jobs_router
from services.jobseeker_service.app.api.applications.router import router as applications_router
from services.jobseeker_service.app.api.notifications.router import router as notifications_router
from services.jobseeker_service.app.api.preferences.router import router as preferences_router
from services.jobseeker_service.app.api.companies.router import router as companies_router
from services.admin_service.app.api.master_data.router import router as master_data_router
from services.admin_service.app.api.support.router import router as support_router
from services.admin_service.app.api.banners.router import router as banners_router

PREFIX = "/api/v1/jobseeker"

def register_routes(app: FastAPI) -> None:
    app.include_router(auth_router, prefix=PREFIX)
    app.include_router(profile_router, prefix=PREFIX)
    app.include_router(jobs_router, prefix=PREFIX)
    app.include_router(companies_router, prefix=PREFIX)
    app.include_router(applications_router, prefix=PREFIX)
    app.include_router(notifications_router, prefix=PREFIX)
    app.include_router(preferences_router, prefix=PREFIX)
    app.include_router(master_data_router, prefix=PREFIX)
    app.include_router(master_data_router, prefix="/api/v1")
    # Support submission routes (accessible via /api/v1/jobseeker/support and /api/v1/support)
    app.include_router(support_router, prefix=PREFIX)
    app.include_router(support_router, prefix="/api/v1")

    # Banner delivery routes
    app.include_router(banners_router, prefix=PREFIX)
    app.include_router(banners_router, prefix="/api/v1")
