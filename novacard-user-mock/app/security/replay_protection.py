from __future__ import annotations

from redis.exceptions import RedisError

from app.clients.redis_client import get_redis


class ReplayError(Exception):
    pass


async def ensure_not_replayed(jti: str, ttl_seconds: int) -> None:
    if not jti:
        # ✅ If there is no jti, fail closed (security first)
        raise ReplayError("missing jti")

    ttl_seconds = max(1, int(ttl_seconds))

    r = get_redis()
    try:
        key = f"svc:jti:{jti}"
        # redis-py returns True on success, None on NX conflict
        ok = await r.set(key, b"1", ex=ttl_seconds, nx=True)

        if not ok:
            raise ReplayError("replayed jti")

    except RedisError as e:
        raise RuntimeError(f"redis_unavailable: {e}") from e