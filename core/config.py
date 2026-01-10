import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME: str = "Own IDE"
    PROJECT_VERSION: str = "1.0.0"

    # MonogoDB settings
    DATABASE_URI: str = os.getenv("DATABASE_URI")
    SUBMISSION_TTL_SECONDS: int = int(os.getenv("SUBMISSION_TTL_SECONDS", "3600"))

    # JWT settings
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )

    # Redis quota settings
    REDIS_URL: str = os.getenv("REDIS_URL")
    GUEST_QUOTA: int = int(os.getenv("GUEST_QUOTA", "1"))
    IP_EXPIRY_SECONDS: int = int(os.getenv("IP_EXPIRY_SECONDS", "86400"))

    # language to Docker image mapping
    LANG_IMAGE = {
        "python": "python:3.12-alpine",
        "javascript": "node:20-alpine",
        "java": "eclipse-temurin:21-jdk-alpine",
        "cpp": "gcc:13.4.0-bookworm",
    }

    # command templates for executing code in different languages
    EXEC_CMD = {
        "python": ["python3", "-c"],
        "javascript": ["node", "-e"],
    }


settings = Settings()
