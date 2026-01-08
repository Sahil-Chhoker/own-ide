from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.server_api import ServerApi
from core.config import settings

_client: AsyncMongoClient | None = None


async def get_client() -> AsyncMongoClient:
    global _client

    if _client is None:
        uri = settings.DATABASE_URI
        _client = AsyncMongoClient(
            uri,
            server_api=ServerApi(version="1", strict=True, deprecation_errors=True),
        )

        # Optional: verify once
        await _client.admin.command({"ping": 1})
        print("Mongo connected")

    return _client


async def close_client():
    global _client
    if _client:
        await _client.close()
        _client = None


async def get_db() -> AsyncDatabase:
    client = await get_client()
    return client.get_database("ideall")
