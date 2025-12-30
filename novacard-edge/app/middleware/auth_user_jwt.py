from __future__ import annotations

from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings
from app.utils.audit_log import audit_log

PUBLIC_PREFIXES = ("/health", "/metrics", "/docs", "/openapi", "/auth")


class UserAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith(PUBLIC_PREFIXES):
            return await call_next(request)

        auth = request.headers.get("authorization", "")
        if not auth.lower().startswith("bearer "):
            audit_log(
                service="edge",
                event="user_auth_failed",
                request_id=getattr(request.state, "request_id", None),
                path=str(request.url.path),
                method=request.method,
                status_code=401,
                detail="missing_token",  # or str(e)
            )
            return JSONResponse({"error": "missing_token"}, status_code=401)

        token = auth.split(" ", 1)[1].strip()

        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid") or settings.USER_JWT_ACTIVE_KID

            secret = settings.USER_JWT_KEYS.get(kid)
            if not secret:
                audit_log(
                    service="edge",
                    event="user_auth_failed",
                    request_id=getattr(request.state, "request_id", None),
                    path=str(request.url.path),
                    method=request.method,
                    status_code=401,
                    detail="unknown_kid",  # or str(e)
                )
                return JSONResponse(
                    {
                        "error": "invalid_token",
                        "detail": f"unknown_kid={kid}",
                        "known_kids": list(settings.USER_JWT_KEYS.keys()),
                    },
                    status_code=401,
                )

            claims = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                issuer=settings.USER_JWT_ISSUER,
                audience=settings.USER_JWT_AUDIENCE,
                options={"verify_exp": True},
            )

            request.state.user_id = claims.get("sub") or "unknown"
            request.state.scopes = claims.get("scope") or ""

        except ExpiredSignatureError:
            return JSONResponse({"error": "token_expired"}, status_code=401)
        except JWTError as e:
            audit_log(
                service="edge",
                event="user_auth_failed",
                request_id=getattr(request.state, "request_id", None),
                path=str(request.url.path),
                method=request.method,
                status_code=401,
                detail="missing_token",  # or str(e)
            )
            return JSONResponse({"error": "invalid_token", "detail": str(e)}, status_code=401)

        return await call_next(request)
