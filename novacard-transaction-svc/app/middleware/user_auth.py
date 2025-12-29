from __future__ import annotations

from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings

PUBLIC_PREFIXES = ("/health", "/metrics", "/docs", "/openapi.json")


class UserAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Allow health/metrics/docs without token
        if path.startswith(PUBLIC_PREFIXES):
            return await call_next(request)

        hdr = request.headers.get("authorization", "")
        if not hdr.lower().startswith("bearer "):
            return JSONResponse({"detail": "missing_token"}, status_code=401)

        token = hdr.split(" ", 1)[1].strip()
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")

            # keyring lookup
            if kid:
                secret = settings.USER_JWT_KEYS.get(kid)
            else:
                # fallback to active kid if token has no kid
                secret = settings.USER_JWT_KEYS.get(settings.USER_JWT_ACTIVE_KID)

            if not secret:
                return JSONResponse(
                    {
                        "detail": "invalid_token",
                        "reason": "unknown_kid",
                        "kid": kid,
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

            sub = claims.get("sub")
            if not sub:
                return JSONResponse({"detail": "invalid_token", "reason": "missing_sub"}, status_code=401)

            # Set user context for routes/services
            
            request.state.user_id = str(sub)
            print("user_id =", request.state.user_id)
            request.state.scopes = claims.get("scope", "")
            request.state.user_claims = claims

        except ExpiredSignatureError:
            return JSONResponse({"detail": "token_expired"}, status_code=401)
        except JWTError as e:
            return JSONResponse({"detail": "invalid_token", "reason": str(e)}, status_code=401)

        return await call_next(request)