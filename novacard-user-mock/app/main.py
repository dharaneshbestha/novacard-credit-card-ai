from __future__ import annotations

import asyncio
import time
import uuid
from typing import Annotated

from fastapi import Body, FastAPI, Request
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from app.middleware_request_signing import RequestSigningMiddleware
from app.middleware_service_auth import ServiceAuthMiddleware

app = FastAPI(title="NovaCard User Mock")

app.add_middleware(RequestSigningMiddleware)
app.add_middleware(ServiceAuthMiddleware)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/users/me")
async def me(request: Request):
    user_id = request.headers.get("x-user-id", "unknown")
    return {
        "user_id": user_id,
        "email": "test@novacard.ai",
        "phone": "+1-000-000-0000",
        "kyc_status": "NOT_STARTED",
        "created_at": "2025-12-18T00:00:00Z",
        "profile": {"first_name": "Test", "last_name": "User", "country": "US", "state": "NJ"},
    }

@app.get("/users/sleep")
async def sleep(seconds: int = 6):
    await asyncio.sleep(seconds)
    return {"slept": seconds}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/users/profile")
async def update_profile(payload: Annotated[dict, Body(...)]):
    return {"ok": True, "request_uuid": str(uuid.uuid4()), "ts": int(time.time()), "payload": payload}