import redis.asyncio as redis
from core.config import settings

_redis_client: redis.Redis | None = None


async def get_redis_client() -> redis.Redis:
    global _redis_client

    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        # Verify connection
        await _redis_client.ping()
        print("Connected to Redis!")

    return _redis_client


async def close_redis():
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
