from __future__ import annotations

import json

import jwt  # pyjwt
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings


def _keys() -> dict[str, str]:
    try:
        return json.loads(settings.SVC_KEYS_JSON)
    except Exception:
        return {}


class ServiceAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Only protect /admin/*
        if not request.url.path.startswith("/admin"):
            return await call_next(request)

        auth = request.headers.get("authorization") or ""
        if not auth.lower().startswith("bearer "):
            return JSONResponse({"detail": "missing_service_token"}, status_code=401)

        token = auth.split(" ", 1)[1].strip()
        try:
            hdr = jwt.get_unverified_header(token)
            kid = hdr.get("kid")
            keys = _keys()
            secret = keys.get(kid)
            if not secret:
                return JSONResponse({"detail": "unknown_kid"}, status_code=401)

            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                audience=settings.SVC_AUDIENCE,
                issuer=settings.SVC_ISSUER,
            )

            # optional: ensure caller is edge
            if payload.get("sub") != "novacard-edge":
                return JSONResponse({"detail": "invalid_service_subject"}, status_code=401)

            request.state.svc = payload
            return await call_next(request)

        except jwt.ExpiredSignatureError:
            return JSONResponse({"detail": "service_token_expired"}, status_code=401)
        except Exception:
            return JSONResponse({"detail": "invalid_service_token"}, status_code=401)
