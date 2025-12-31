from __future__ import annotations

import time

from fastapi import FastAPI, Request

from app.metrics import http_latency_seconds, http_requests_total, service_up
from app.middleware.exceptions import unhandled_exception_handler
from app.middleware.service_auth import ServiceAuthMiddleware
from app.middleware.structured_logging import RequestContextMiddleware
from app.middleware.user_auth import UserAuthMiddleware
from app.routes.admin_drift import router as admin_drift_router
from app.routes.health import router as health_router
from app.routes.metrics import router as metrics_router
from app.routes.purchase import router as purchase_router

app = FastAPI(title="NovaCard Transaction Service", version="0.1.0")
app.add_middleware(RequestContextMiddleware, service="transaction")
app.state.service_name = "transaction"
app.add_exception_handler(Exception, unhandled_exception_handler)
app.add_middleware(UserAuthMiddleware)
app.add_middleware(ServiceAuthMiddleware)
app.include_router(health_router)
app.include_router(purchase_router)
app.include_router(metrics_router)
app.include_router(admin_drift_router)

service_up.set(1)


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
