import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from redis.exceptions import RedisError

from app.clients.redis_client import get_redis
from app.middleware.auth_user_jwt import UserAuthMiddleware
from app.middleware.exceptions import unhandled_exception_handler
from app.middleware.idempotency import IdempotencyMiddleware
from app.middleware.logging import LoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_context import RequestContextMiddleware
from app.middleware.request_id import RequestIdMiddleware
from app.routing.proxy import router as proxy_router
from app.routing.routes import router as system_router
from app.routing.transactions import router as transactions_router

app = FastAPI(title="NovaCard Edge API", version="0.1.0")
app.add_middleware(RequestContextMiddleware, service="edge")
app.state.service_name = "edge"
app.add_exception_handler(Exception, unhandled_exception_handler)
# Middleware order matters:
# request id -> logging -> rate limit -> auth -> idempotency -> routes
app.add_middleware(RequestIdMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(UserAuthMiddleware)  # auth
app.add_middleware(
    IdempotencyMiddleware,
    protected_prefixes=["/users/profile"],  # start small; expand later
)
app.include_router(system_router)
app.include_router(proxy_router)
app.include_router(transactions_router)


@app.middleware("http")
async def request_id_mw(request: Request, call_next):
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = rid
    resp = await call_next(request)
    resp.headers["X-Request-Id"] = rid
    return resp


@app.get("/health/redis")
async def health_redis():
    try:
        r = get_redis()
        pong = await r.ping()
        return {"status": "ok", "redis": "up", "ping": bool(pong)}
    except RedisError as e:
        return JSONResponse({"status": "degraded", "redis": "down", "detail": str(e)}, status_code=503)
    except Exception as e:
        return JSONResponse({"status": "degraded", "redis": "down", "detail": str(e)}, status_code=503)


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
