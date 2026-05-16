import asyncio
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.server_api import ServerApi
from core.config import settings

_client: AsyncMongoClient | None = None
_indexes_ensured = False
_index_lock = asyncio.Lock()


async def get_client() -> AsyncMongoClient:
    global _client

    if _client is None:
        uri = settings.DATABASE_URI
        if uri.startswith("mongodb+srv://"):
            _client = AsyncMongoClient(
                uri,
                server_api=ServerApi(version="1", strict=True, deprecation_errors=True),
            )
        else:
            _client = AsyncMongoClient(uri)

        # Verify once
        await _client.admin.command({"ping": 1})

    return _client


async def close_client():
    global _client
    if _client:
        await _client.close()
        _client = None


async def get_db() -> AsyncDatabase:
    client = await get_client()
    db = client.get_database(settings.DATABASE_NAME)

    await ensure_indexes(db)
    return db


async def ensure_indexes(db: AsyncDatabase) -> None:
    """Create essential indexes once per process."""
    global _indexes_ensured
    if _indexes_ensured:
        return

    async with _index_lock:
        if _indexes_ensured:
            return

        # TTL cleanup for submissions and unique constraints for users.
        await db.submissions.create_index("expireAt", expireAfterSeconds=0)
        await db.users.create_index("username", unique=True)
        await db.users.create_index("email", unique=True)
        _indexes_ensured = True
