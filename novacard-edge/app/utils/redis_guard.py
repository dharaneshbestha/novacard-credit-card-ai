from __future__ import annotations

from fastapi import HTTPException
from redis.exceptions import RedisError

from app.clients.redis_client import get_redis


async def require_redis() -> None:
    try:
        r = get_redis()
        await r.ping()
    except (RedisError, Exception) as e:
        raise HTTPException(status_code=503, detail=f"redis_unavailable: {e}")