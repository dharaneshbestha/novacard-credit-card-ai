from __future__ import annotations

import time
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings
from app.metrics_security import user_security_events_total
from app.security.replay_protection import ensure_not_replayed, ReplayError
from app.utils.audit_log import audit_log

PUBLIC_PATHS = {"/health", "/metrics"}


class ServiceAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        request_id = request.headers.get("x-request-id")
        path = str(request.url.path)
        method = request.method

        hdr = request.headers.get("x-service-authorization", "")
        if not hdr.startswith("Bearer "):
            user_security_events_total.labels(event="service_auth", result="missing_token", kid="none").inc()
            audit_log(
                service="user",
                event="service_auth_failed",
                request_id=request_id,
                path=path,
                method=method,
                status_code=401,
                detail="missing_service_token",
            )
            return JSONResponse({"error": "missing_service_token"}, status_code=401)

        token = hdr.split(" ", 1)[1].strip()

        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            kid_label = str(kid or "none")
            if not kid:
                user_security_events_total.labels(event="service_auth", result="missing_kid", kid="none").inc()
                audit_log(
                    service="user",
                    event="service_auth_failed",
                    request_id=request_id,
                    path=path,
                    method=method,
                    status_code=401,
                    detail="missing_kid",
                )
                return JSONResponse({"error": "missing_kid"}, status_code=401)

            secret = settings.SVC_KEYS.get(kid)
            if not secret:
                user_security_events_total.labels(event="service_auth", result="unknown_kid", kid=kid_label).inc()
                audit_log(
                    service="user",
                    event="service_auth_failed",
                    request_id=request_id,
                    path=path,
                    method=method,
                    status_code=401,
                    detail=f"unknown_kid={kid}",
                    extra={"known_kids": list(settings.SVC_KEYS.keys())},
                )
                return JSONResponse({"error": "invalid_service_token", "detail": f"unknown_kid={kid}"}, status_code=401)

            claims = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                issuer=settings.SVC_EXPECTED_ISSUER,
                audience=settings.SVC_AUDIENCE,
                options={"verify_exp": True},
            )

            # Strict time checks
            now = int(time.time())
            iat = int(claims.get("iat", 0))
            exp = int(claims.get("exp", 0))
            SKEW = 30

            if exp <= now - SKEW:
                user_security_events_total.labels(event="service_auth", result="expired", kid=kid_label).inc()
                audit_log(
                    service="user",
                    event="service_auth_failed",
                    request_id=request_id,
                    path=path,
                    method=method,
                    status_code=401,
                    detail="service_token_expired",
                    extra={"kid": kid_label},
                )
                return JSONResponse({"error": "service_token_expired"}, status_code=401)

            if iat > now + SKEW:
                user_security_events_total.labels(event="service_auth", result="iat_in_future", kid=kid_label).inc()
                audit_log(
                    service="user",
                    event="service_auth_failed",
                    request_id=request_id,
                    path=path,
                    method=method,
                    status_code=401,
                    detail="service_token_iat_in_future",
                    extra={"kid": kid_label},
                )
                return JSONResponse({"error": "service_token_iat_in_future"}, status_code=401)

            if not claims.get("svc"):
                user_security_events_total.labels(event="service_auth", result="missing_svc_claim", kid=kid_label).inc()
                audit_log(
                    service="user",
                    event="service_auth_failed",
                    request_id=request_id,
                    path=path,
                    method=method,
                    status_code=401,
                    detail="missing_svc_claim",
                    extra={"kid": kid_label},
                )
                return JSONResponse({"error": "invalid_service_token", "detail": "missing svc claim"}, status_code=401)

            # Replay protection (fail closed if unavailable)
            jti = claims.get("jti")
            if not jti:
                user_security_events_total.labels(event="service_auth", result="missing_jti", kid=kid_label).inc()
                audit_log(
                    service="user",
                    event="service_auth_failed",
                    request_id=request_id,
                    path=path,
                    method=method,
                    status_code=401,
                    detail="missing_jti",
                    extra={"kid": kid_label},
                )
                return JSONResponse({"error": "invalid_service_token", "detail": "missing jti"}, status_code=401)

            ttl = max(1, exp - now)
            try:
                await ensure_not_replayed(jti, ttl_seconds=ttl)
            except ReplayError as e:
                user_security_events_total.labels(event="service_auth", result="replay_blocked", kid=kid_label).inc()
                audit_log(
                    service="user",
                    event="service_token_replay_blocked",
                    request_id=request_id,
                    path=path,
                    method=method,
                    status_code=401,
                    detail=f"replayed jti",
                    extra={"kid": kid_label, "svc": claims.get("svc"), "jti": jti},
                )
                return JSONResponse({"error": "replayed_service_token", "kid": kid_label, "svc": claims.get("svc"), "detail": "replayed jti"}, status_code=401)
            except Exception as e:
                user_security_events_total.labels(event="service_auth", result="replay_unavailable", kid=kid_label).inc()
                audit_log(
                    service="user",
                    event="replay_protection_unavailable",
                    request_id=request_id,
                    path=path,
                    method=method,
                    status_code=503,
                    detail=str(e),
                    extra={"kid": kid_label},
                )
                return JSONResponse({"error": "replay_protection_unavailable", "detail": str(e)}, status_code=503)

            # ✅ Only after replay passes: mark success
            user_security_events_total.labels(event="service_auth", result="success", kid=kid_label).inc()
            audit_log(
                service="user",
                event="service_auth_success",
                request_id=request_id,
                path=path,
                method=method,
                extra={"kid": kid_label, "svc": claims.get("svc"), "jti": jti},
            )

            request.state.service_claims = claims
            return await call_next(request)

        except ExpiredSignatureError:
            user_security_events_total.labels(event="service_auth", result="expired", kid="none").inc()
            audit_log(
                service="user",
                event="service_auth_failed",
                request_id=request_id,
                path=path,
                method=method,
                status_code=401,
                detail="service_token_expired",
            )
            return JSONResponse({"error": "service_token_expired"}, status_code=401)

        except JWTError as e:
            # Try to extract kid for labeling if possible
            kid_label = "none"
            try:
                hdr2 = jwt.get_unverified_header(token)
                kid_label = str(hdr2.get("kid") or "none")
            except Exception:
                pass

            user_security_events_total.labels(event="service_auth", result="invalid_token", kid=kid_label).inc()
            audit_log(
                service="user",
                event="service_auth_failed",
                request_id=request_id,
                path=path,
                method=method,
                status_code=401,
                detail=f"invalid_service_token: {str(e)}",
                extra={"kid": kid_label},
            )
            return JSONResponse({"error": "invalid_service_token", "detail": str(e)}, status_code=401)