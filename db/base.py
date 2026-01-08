from pymongo.asynchronous.database import AsyncDatabase
from db.session import get_client

async def get_db() -> AsyncDatabase:
    client = await get_client()
    return client.get_database("ideall")