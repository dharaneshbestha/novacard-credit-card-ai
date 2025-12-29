from __future__ import annotations

import base64
import hashlib
import hmac
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings
from app.metrics_security import user_security_events_total
from app.utils.audit_log import audit_log

PUBLIC_PATHS = {"/health", "/metrics"}


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode((s + pad).encode("utf-8"))


def _body_sha256_hex(body: bytes | None) -> str:
    return hashlib.sha256(body or b"").hexdigest()


def _canonical_string(method: str, path: str, query: str, ts: int, body_hash: str) -> str:
    # MUST match edge canonical string exactly
    return "\n".join([
        method.upper(),
        path,
        query or "",
        str(ts),
        body_hash,
    ])


class RequestSigningMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_PATHS or not settings.SIGNING_REQUIRED:
            return await call_next(request)

        # We intentionally reuse the label name "kid" to keep a consistent metric dimension.
        # For signatures, kid == signature key id.
        key_id = request.headers.get("x-signature-keyid")
        kid_label = str(key_id or "none")

        ts_str = request.headers.get("x-signature-timestamp")
        content_sha = request.headers.get("x-content-sha256")
        sig = request.headers.get("x-signature")

        request_id = request.headers.get("x-request-id")
        path = str(request.url.path)
        method = request.method

        def _fail(detail: str, status: int = 401):
            user_security_events_total.labels(event="request_signature", result="failed", kid=kid_label).inc()
            audit_log(
                service="user",
                event="request_signature_failed",
                request_id=request_id,
                path=path,
                method=method,
                status_code=status,
                detail=detail,
                extra={"kid": kid_label},
            )
            return JSONResponse({"error": "invalid_signature", "detail": detail}, status_code=status)

        if not (key_id and ts_str and content_sha and sig):
            return _fail("missing_signature_headers")

        if key_id != settings.SIGNING_KEY_ID:
            return _fail(f"invalid_signature_keyid expected={settings.SIGNING_KEY_ID} got={key_id}")

        try:
            ts = int(ts_str)
        except ValueError:
            return _fail("invalid_signature_timestamp")

        now = int(time.time())
        if abs(now - ts) > int(settings.SIGNING_TOLERANCE_SECONDS):
            return _fail("signature_timestamp_out_of_window")

        body = await request.body()
        computed_hash = _body_sha256_hex(body)
        if computed_hash != content_sha:
            return _fail("content_hash_mismatch")

        canon = _canonical_string(
            method=method,
            path=path,
            query=request.url.query,
            ts=ts,
            body_hash=content_sha,
        ).encode("utf-8")

        expected = hmac.new(
            settings.SIGNING_SECRET.encode("utf-8"),
            canon,
            hashlib.sha256,
        ).digest()

        try:
            provided = _b64url_decode(sig)
        except Exception:
            return _fail("invalid_signature_encoding")

        if not hmac.compare_digest(expected, provided):
            return _fail("invalid_signature")

        # ✅ Only here we mark success (all checks passed)
        user_security_events_total.labels(event="request_signature", result="success", kid=kid_label).inc()
        audit_log(
            service="user",
            event="request_signature_success",
            request_id=request_id,
            path=path,
            method=method,
            extra={"kid": kid_label},
        )

        return await call_next(request)