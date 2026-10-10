import logging

from apis.base import api_router
from fastapi import FastAPI
from core.config import settings
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from db.db_session import get_client
from db.redis_session import get_redis_client

logger = logging.getLogger(__name__)


def start_application() -> FastAPI:
    app = FastAPI(title=settings.PROJECT_NAME, version=settings.PROJECT_VERSION)
    app.include_router(api_router)

    # Set all CORS enabled origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


app = start_application()


@app.get("/", tags=["home"])
def home():
    return {"message": "Welcome to the Own IDE API! Go to /docs to test this API."}

@app.get("/health", tags=["health"])
async def health():
    checks: dict[str, str] = {}

    try:
        mongo_client = await get_client()
        await mongo_client.admin.command({"ping": 1})
        checks["database"] = "ok"
    except Exception:
        logger.exception("Health check failed for MongoDB")
        checks["database"] = "unavailable"

    try:
        redis_client = await get_redis_client()
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception:
        logger.exception("Health check failed for Redis")
        checks["redis"] = "unavailable"

    is_healthy = all(check == "ok" for check in checks.values())
    return JSONResponse(
        status_code=200 if is_healthy else 503,
        content={
            "status": "ok" if is_healthy else "unavailable",
            "checks": checks,
        },
    )
