from fastapi import FastAPI
from apis.v1.route_user import router as user_router
from apis.v1.route_login import router as login_router

app = FastAPI()
app.include_router(user_router, prefix="/api/user", tags=["user"])
app.include_router(login_router, prefix="/api/user", tags=["login"])