from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.clients.redis_client import get_redis
from app.config import settings
from app.utils.redis_guard import require_redis


def _window_key(prefix: str, window_seconds: int) -> str:
    bucket = int(time.time()) // window_seconds
    return f"{prefix}:{bucket}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if (
            path.startswith("/health")
            or path.startswith("/metrics")
            or path.startswith("/docs")
            or path.startswith("/openapi")
        ):
            return await call_next(request)

        await require_redis()
        r = get_redis()

        user_id = getattr(request.state, "user_id", None)
        ip = request.headers.get("x-forwarded-for")
        if ip:
            ip = ip.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        if user_id:
            limit = settings.RL_AUTHD_PER_USER_PER_MIN
            key = _window_key(f"rl:user:{user_id}", 60)
        else:
            limit = (
                settings.RL_AUTH_PER_IP_PER_MIN
                if path.startswith("/auth")
                else settings.RL_PUBLIC_PER_IP_PER_MIN
            )
            key = _window_key(f"rl:ip:{ip}", 60)

        window_seconds = 60
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, window_seconds)

        reset_epoch = ((int(time.time()) // window_seconds) + 1) * window_seconds
        remaining = max(0, int(limit) - int(count))
        common_headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_epoch),
        }

        if int(count) > int(limit):
            retry_after = max(0, reset_epoch - int(time.time()))
            hdrs = dict(common_headers)
            hdrs["Retry-After"] = str(retry_after)
            return JSONResponse(
                {"error": "rate_limited", "limit_per_min": int(limit)}, status_code=429, headers=hdrs
            )

        response = await call_next(request)
        for k, v in common_headers.items():
            response.headers[k] = v
        return response
