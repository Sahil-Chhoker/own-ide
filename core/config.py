import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME: str = "Own IDE"
    PROJECT_VERSION: str = "1.0.0"

    DATABASE_URI: str = os.getenv("DATABASE_URI", "mongodb://localhost:27017")
    SECRET_KEY: str = os.getenv("SECRET_KEY")  # type: ignore
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )

    # language to Docker image mapping
    LANG_IMAGE = {
        "python": "python:3.12-alpine",
        "javascript": "node:20-alpine",
        "java": "eclipse-temurin:21-jdk-alpine",
        "cpp": "gcc:13.4.0-bookworm",
    }

    EXEC_CMD = {
        "python": ["python3", "-c"],
        "javascript": ["node", "-e"],
    }


settings = Settings()
