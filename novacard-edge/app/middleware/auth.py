from __future__ import annotations

import time

from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings
from app.metrics_security import edge_security_events_total
from app.utils.audit_log import audit_log

# Allow docs/health/metrics and auth routes without user token
PUBLIC_PREFIXES = (
    "/health",
    "/metrics",
    "/docs",
    "/openapi.json",
    "/auth/",
    "/.well-known/",
)


def _is_public_path(path: str) -> bool:
    return any(path == p or path.startswith(p) for p in PUBLIC_PREFIXES)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Validates end-user JWT in Authorization: Bearer <token>
    Stores:
      - request.state.user_id
      - request.state.scopes
    """

    async def dispatch(self, request: Request, call_next):
        path = str(request.url.path)
        method = request.method.upper()

        if _is_public_path(path):
            return await call_next(request)

        request_id = getattr(request.state, "request_id", None)

        hdr = request.headers.get("authorization", "")
        if not hdr.startswith("Bearer "):
            edge_security_events_total.labels(event="user_auth", result="missing_token").inc()
            audit_log(
                service="edge",
                event="user_auth_failed",
                request_id=request_id,
                path=path,
                method=method,
                status_code=401,
                detail="missing_token",
            )
            return JSONResponse({"error": "missing_token"}, status_code=401)

        token = hdr.split(" ", 1)[1].strip()

        try:
            # Read kid without verifying (to choose key)
            header = jwt.get_unverified_header(token)
            kid = header.get("kid") or settings.USER_JWT_ACTIVE_KID
            secret = settings.USER_JWT_KEYS.get(kid)

            if not secret:
                edge_security_events_total.labels(event="user_auth", result="invalid_token").inc()
                audit_log(
                    service="edge",
                    event="user_auth_failed",
                    request_id=request_id,
                    path=path,
                    method=method,
                    status_code=401,
                    detail=f"unknown_kid={kid}",
                )
                return JSONResponse(
                    {"error": "invalid_token", "detail": f"unknown_kid={kid}"}, status_code=401
                )

            claims = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                issuer=settings.USER_JWT_ISSUER,
                audience=settings.USER_JWT_AUDIENCE,
                options={"verify_exp": True},
            )

            # Basic sanity (clock skew guard)
            now = int(time.time())
            exp = int(claims.get("exp", 0))
            if exp and exp < now:
                raise ExpiredSignatureError("expired")

            user_id: str | None = claims.get("sub")
            scope = claims.get("scope", "")
            scopes = scope.split() if isinstance(scope, str) else []

            request.state.user_id = user_id
            request.state.scopes = scopes

            edge_security_events_total.labels(event="user_auth", result="success").inc()
            audit_log(
                service="edge",
                event="user_auth_success",
                request_id=request_id,
                user_id=str(user_id) if user_id else None,
            )

            return await call_next(request)

        except ExpiredSignatureError:
            edge_security_events_total.labels(event="user_auth", result="invalid_token").inc()
            audit_log(
                service="edge",
                event="user_auth_failed",
                request_id=request_id,
                path=path,
                method=method,
                status_code=401,
                detail="token_expired",
            )
            return JSONResponse({"error": "invalid_token", "detail": "expired"}, status_code=401)

        except JWTError as e:
            edge_security_events_total.labels(event="user_auth", result="invalid_token").inc()
            audit_log(
                service="edge",
                event="user_auth_failed",
                request_id=request_id,
                path=path,
                method=method,
                status_code=401,
                detail=f"invalid_token: {str(e)}",
            )
            return JSONResponse({"error": "invalid_token", "detail": str(e)}, status_code=401)
