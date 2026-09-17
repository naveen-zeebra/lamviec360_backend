from fastapi import APIRouter
from app.api.v1.auth.seeker_auth import router as seeker_auth_router
from app.api.v1.auth.company_auth import router as company_auth_router
from app.api.v1.auth.admin_auth import router as admin_auth_router
from app.api.v1.public.public_router import router as public_router
from app.api.v1.seeker.seeker_router import router as seeker_router
from app.api.v1.company.company_router import router as company_router
from app.api.v1.admin.admin_router import router as admin_router

api_router = APIRouter()

# Authentication sub-routers (Separated flows)
api_router.include_router(seeker_auth_router)
api_router.include_router(company_auth_router)
api_router.include_router(admin_auth_router)

# Domain workspaces
api_router.include_router(public_router)
api_router.include_router(seeker_router)
api_router.include_router(company_router)
api_router.include_router(admin_router)
