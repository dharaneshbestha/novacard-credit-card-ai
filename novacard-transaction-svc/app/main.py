from __future__ import annotations

import time
from fastapi import FastAPI, Request
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.metrics import http_requests_total, http_latency_seconds, service_up
from app.routes.health import router as health_router
from app.routes.purchase import router as purchase_router
from app.middleware.user_auth import UserAuthMiddleware
from fastapi.responses import Response

app = FastAPI(title="NovaCard Transaction Service", version="0.1.0")
app.add_middleware(UserAuthMiddleware)
app.include_router(health_router)
app.include_router(purchase_router)

service_up.set(1)

@app.get("/metrics")
async def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

@app.middleware("http")
async def metrics_mw(request: Request, call_next):
    path = request.url.path
    method = request.method
    start = time.time()
    try:
        with http_latency_seconds.labels(path=path, method=method).time():
            resp = await call_next(request)
        http_requests_total.labels(path=path, method=method, status=str(resp.status_code)).inc()
        return resp
    except Exception:
        http_requests_total.labels(path=path, method=method, status="500").inc()
        raise
    finally:
        _ = time.time() - start