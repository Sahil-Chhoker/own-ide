import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Own IDE"
    PROJECT_VERSION: str = "1.0.0"

    DATABASE_URI: str = os.getenv("DATABASE_URI", "mongodb://localhost:27017")
    SECRET_KEY: str = os.getenv("SECRET_KEY") # type: ignore
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

settings = Settings()