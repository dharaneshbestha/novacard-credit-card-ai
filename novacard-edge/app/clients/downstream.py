from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import random
import time
import uuid

import httpx
from jose import jwt
from starlette.requests import Request

from app.config import settings
from app.metrics import downstream_latency_seconds, downstream_requests_total, set_circuit_state
from app.metrics_security import edge_security_events_total
from app.utils.circuit_breaker import CircuitBreaker
from app.utils.downstream_errors import DownstreamError

# ---- retry config ----
IDEMPOTENT_METHODS = {"GET", "HEAD", "OPTIONS"}
MAX_RETRIES = 2               # total attempts = 1 + MAX_RETRIES
BASE_BACKOFF_SECONDS = 0.25
MAX_BACKOFF_SECONDS = 2.0

CIRCUIT_RETRY_AFTER_SECONDS = 30  # keep in sync with breaker open cooldown


def _backoff(attempt: int) -> float:
    exp = min(MAX_BACKOFF_SECONDS, BASE_BACKOFF_SECONDS * (2 ** attempt))
    jitter = random.uniform(0, 0.1)
    return exp + jitter


def _sha256_hex(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _canonical_string(method: str, path: str, query: str, ts: int, body_hash: str) -> bytes:
    # MUST match user-mock canonical string exactly
    return "\n".join([
        method.upper(),
        path,
        query or "",
        str(ts),
        body_hash,
    ]).encode("utf-8")


def _sign_request(method: str, path: str, query: str, body: bytes) -> dict[str, str]:
    """
    HMAC signing headers required by downstream services (user-mock today).
    Uses EDGE signing secret & key id.
    """
    ts = int(time.time())
    body_hash = _sha256_hex(body)
    canon = _canonical_string(method, path, query, ts, body_hash)
    mac = hmac.new(settings.SIGNING_SECRET.encode("utf-8"), canon, hashlib.sha256).digest()
    sig = _b64url(mac)

    return {
        "X-Signature-KeyId": settings.SIGNING_KEY_ID,
        "X-Signature-Timestamp": str(ts),
        "X-Content-SHA256": body_hash,
        "X-Signature": sig,
    }


class DownstreamClient:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=15.0)

        # Circuit breakers per service
        self.breakers = {
            "auth": CircuitBreaker(),
            "user": CircuitBreaker(),
            "kyc": CircuitBreaker(),
            "account": CircuitBreaker(),
            "transaction": CircuitBreaker(), 
        }

    def _build_service_token(self, *, audience: str) -> str:
        """
        Service-to-service JWT (HS256) with keyring kid.
        MUST be unique per request (unique jti) for replay protection.
        """
        kid = settings.SVC_ACTIVE_KID
        secret = settings.SVC_KEYS.get(kid)
        if not secret:
            raise DownstreamError("edge", "config_error", f"unknown svc kid={kid}")

        now = int(time.time())
        claims = {
            "iss": settings.SVC_ISSUER,
            "aud": audience,
            "iat": now,
            "exp": now + settings.SVC_TOKEN_TTL_SECONDS,
            "jti": str(uuid.uuid4()),
            "svc": settings.SERVICE_NAME,
        }

        token = jwt.encode(
            claims,
            secret,
            algorithm="HS256",
            headers={"kid": kid, "typ": "JWT"},
        )
        return token

    async def forward(
        self,
        request: Request,
        base_url: str,
        audience: str,
        service_name: str,
    ) -> httpx.Response:
        breaker = self.breakers.get(service_name)
       
        if not breaker:
            raise DownstreamError(service_name, "config_error", "missing breaker for service")

        # ---- build URL safely ----
        forward_path = getattr(request.state, "forward_path", request.url.path)
        url = f"{str(base_url).rstrip('/')}/{forward_path.lstrip('/')}"
        # url = f"{str(base_url).rstrip('/')}/{request.url.path.lstrip('/')}"
        params = dict(request.query_params)

        # ---- method/body ----
        method = request.method.upper()
        body = getattr(request.state, "raw_body", None)
        if body is None:
            body = await request.body()

        # ---- headers: pass-through + normalized ----
        headers = dict(request.headers)
        print("[EDGE] forwarding Idempotency-Key:", headers.get("idempotency-key"))
        headers.pop("host", None)

        request_id = getattr(request.state, "request_id", None)
        user_id = getattr(request.state, "user_id", None)
        scopes = getattr(request.state, "scopes", None)

        if request_id:
            headers["X-Request-Id"] = request_id
        if user_id:
            headers["X-User-Id"] = str(user_id)
        if scopes:
            headers["X-User-Scopes"] = " ".join(scopes) if isinstance(scopes, list) else str(scopes)

        # ---- service-to-service auth: ALWAYS per-request (replay-safe) ----
        svc_token = self._build_service_token(audience=audience)
        headers["X-Service-Authorization"] = f"Bearer {svc_token}"

        # ---- request signing (HMAC) ----
        signing_headers = _sign_request(method, request.url.path, request.url.query, body)
        headers.update(signing_headers)
        edge_security_events_total.labels(event="downstream_signing", result="applied").inc()

        # ---- retries (idempotent only) ----
        attempts = 1 + (MAX_RETRIES if method in IDEMPOTENT_METHODS else 0)

        for attempt in range(attempts):
            set_circuit_state(service_name, breaker.state)

            # circuit check
            if not breaker.allow():
                downstream_requests_total.labels(service=service_name, method=method, result="circuit_open").inc()
                edge_security_events_total.labels(event="downstream_call", result="circuit_open").inc()
                raise DownstreamError(service_name, "circuit_open", f"state={breaker.state}")

            try:
                with downstream_latency_seconds.labels(service=service_name, method=method).time():
                    resp = await self.client.request(
                        method=method,
                        url=url,
                        params=params,
                        headers=headers,
                        content=body,
                        timeout=5.0,
                    )

                # 5xx → breaker failure (+ retry for idempotent)
                if resp.status_code >= 500:
                    breaker.record_failure()
                    set_circuit_state(service_name, breaker.state)
                    downstream_requests_total.labels(service=service_name, method=method, result="5xx").inc()
                    edge_security_events_total.labels(event="downstream_call", result="5xx").inc()

                    if method in IDEMPOTENT_METHODS and attempt < attempts - 1:
                        await asyncio.sleep(_backoff(attempt))
                        continue

                    raise DownstreamError(service_name, "downstream_5xx", f"status={resp.status_code}")

                # non-5xx is considered “success” from transport perspective
                breaker.record_success()
                set_circuit_state(service_name, breaker.state)
                downstream_requests_total.labels(service=service_name, method=method, result="success").inc()
                return resp

            except httpx.TimeoutException:
                breaker.record_failure()
                set_circuit_state(service_name, breaker.state)
                downstream_requests_total.labels(service=service_name, method=method, result="timeout").inc()
                edge_security_events_total.labels(event="downstream_call", result="timeout").inc()

                if method in IDEMPOTENT_METHODS and attempt < attempts - 1:
                    await asyncio.sleep(_backoff(attempt))
                    continue

                raise DownstreamError(service_name, "downstream_timeout", "timeout=5s")

            except httpx.RequestError as e:
                breaker.record_failure()
                set_circuit_state(service_name, breaker.state)
                downstream_requests_total.labels(service=service_name, method=method, result="unreachable").inc()
                edge_security_events_total.labels(event="downstream_call", result="unreachable").inc()

                if method in IDEMPOTENT_METHODS and attempt < attempts - 1:
                    await asyncio.sleep(_backoff(attempt))
                    continue

                raise DownstreamError(service_name, "downstream_unreachable", str(e))

            except DownstreamError:
                # already classified
                raise

            except Exception as e:
                breaker.record_failure()
                set_circuit_state(service_name, breaker.state)
                downstream_requests_total.labels(service=service_name, method=method, result="other_error").inc()
                edge_security_events_total.labels(event="downstream_call", result="other_error").inc()
                raise DownstreamError(service_name, "downstream_error", str(e))