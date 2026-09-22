from fastapi import FastAPI
from services.admin_service.app.api.auth.router import router as auth_router
from services.admin_service.app.api.profile.router import router as profile_router
from services.admin_service.app.api.dashboard.router import router as dashboard_router
from services.admin_service.app.api.users.router import router as users_router
from services.admin_service.app.api.roles.router import router as roles_router
from services.admin_service.app.api.companies.router import router as companies_router
from services.admin_service.app.api.jobs.router import router as jobs_router
from services.admin_service.app.api.audit_logs.router import router as audit_logs_router

routers = [
    auth_router,
    profile_router,
    dashboard_router,
    users_router,
    roles_router,
    companies_router,
    jobs_router,
    audit_logs_router,
]

def register_routes(app: FastAPI) -> None:
    # Register under /api/v1/admin (canonical gateway namespace)
    for r in routers:
        app.include_router(r, prefix="/api/v1/admin")

    # Also register under /api/v1 for standard admin portal frontend compatibility
    for r in routers:
        app.include_router(r, prefix="/api/v1")
