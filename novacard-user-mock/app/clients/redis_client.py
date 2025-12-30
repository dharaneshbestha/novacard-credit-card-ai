from __future__ import annotations

import redis.asyncio as redis
from redis.asyncio.client import Redis

from app.config import settings

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.REDIS_URL, decode_responses=False)
    return _redis
