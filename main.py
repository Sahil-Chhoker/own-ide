from apis.base import api_router
from fastapi import FastAPI
from core.config import settings
from fastapi.middleware.cors import CORSMiddleware


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
    return {"message": "Welcome to the Own IDE API!"}
