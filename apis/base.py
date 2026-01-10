from fastapi import APIRouter
from apis.v1.route_user import router as user_router
from apis.v1.route_login import router as login_router
from apis.v1.route_sandbox import router as sandbox_router

api_router = APIRouter()
api_router.include_router(user_router, prefix="/api/user", tags=["user"])
api_router.include_router(login_router, prefix="/api/user", tags=["user"])
api_router.include_router(sandbox_router, prefix="/api/sandbox", tags=["sandbox"])
