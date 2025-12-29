from __future__ import annotations

import redis.asyncio as redis

from app.config import settings

_r: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    global _r
    if _r is None:
        _r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _r