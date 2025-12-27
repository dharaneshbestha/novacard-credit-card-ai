from __future__ import annotations

from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
from jose import jwt
from app.utils.audit_log import audit_log
from app.config import settings

app = FastAPI(title="NovaCard Mock Auth", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/auth/signup")
async def signup(payload: dict):
    return {
        "user_id": "user_123",
        "status": "pending_verification",
    }


@app.post("/auth/login")
async def login(payload: dict):
    now = datetime.now(tz=timezone.utc)

    kid = settings.ACTIVE_KID
    secret = settings.KEYS.get(kid)
    if not secret:
        return {"error": "config_error", "detail": f"unknown kid={kid}"}

    claims = {
        "sub": "user_123",
        "iss": settings.ISSUER,
        "aud": settings.AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.TOKEN_TTL_SECONDS)).timestamp()),
        "scope": "user",
    }

    token = jwt.encode(
        claims,
        secret,
        algorithm="HS256",
        headers={"kid": kid, "typ": "JWT"},
    )
    audit_log(
        service="auth",
        event="token_issued",
        request_id=None,
        user_id="user_123",
        extra={"kid": kid, "ttl": settings.TOKEN_TTL_SECONDS},
    )
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": settings.TOKEN_TTL_SECONDS,
    }


@app.post("/auth/verify-otp")
async def verify_otp(payload: dict):
    return {"status": "verified"}


@app.post("/auth/refresh")
async def refresh():
    return {"error": "not_implemented"}