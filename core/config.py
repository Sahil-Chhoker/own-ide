import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME: str = "Own IDE"
    PROJECT_VERSION: str = "1.0.0"

    # MongoDB settings
    DATABASE_URI: str = os.getenv("DATABASE_URI", "mongodb://mongo:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "ideall")
    SUBMISSION_TTL_SECONDS: int = int(os.getenv("SUBMISSION_TTL_SECONDS", "3600"))

    # JWT settings
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )

    # Redis quota settings
    REDIS_HOST: str = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_USERNAME: str | None = os.getenv("REDIS_USERNAME") or None
    REDIS_PASSWORD: str | None = os.getenv("REDIS_PASSWORD") or None
    GUEST_QUOTA: int = int(os.getenv("GUEST_QUOTA", "1"))
    IP_EXPIRY_SECONDS: int = int(os.getenv("IP_EXPIRY_SECONDS", "86400"))

    # Celery (defaults share Redis with quota; use separate URLs in prod if you prefer)
    REDIS_URL: str = os.getenv(
        "REDIS_URL",
        f"redis://{REDIS_HOST}:{REDIS_PORT}/0",
    )
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL") or REDIS_URL
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND") or REDIS_URL

    # language to Docker image mapping
    LANG_IMAGE = {
        "python": "python:3.12-alpine",
        "javascript": "node:20-alpine",
        "java": "eclipse-temurin:21-jdk-alpine",
        "cpp": "gcc:13.4.0-bookworm",
    }



settings = Settings()
