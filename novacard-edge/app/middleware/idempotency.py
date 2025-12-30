import hashlib
import json
from collections.abc import Iterable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.clients.redis_client import get_redis
from app.config import settings
from app.utils.redis_guard import require_redis


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    MVP idempotency for POST on selected route prefixes.
    - Requires Idempotency-Key header.
    - Stores response in Redis and replays it on retries.
    - Uses a short Redis lock to prevent duplicate in-flight downstream calls.
    """

    def __init__(self, app, protected_prefixes: Iterable[str]):
        super().__init__(app)
        self.protected_prefixes = tuple(protected_prefixes)

    def _is_protected(self, request: Request) -> bool:
        path = request.url.path
        return any(path.startswith(p) for p in self.protected_prefixes)

    async def dispatch(self, request: Request, call_next):
        # Only enforce on POST for now
        method = request.method.upper()
        if method != "POST":
            return await call_next(request)

        if not self._is_protected(request):
            return await call_next(request)

        # Fail closed if Redis is unavailable (fintech-safe)
        await require_redis()
        r = get_redis()

        idem_key = request.headers.get("Idempotency-Key")
        if not idem_key:
            return JSONResponse({"error": "missing_idempotency_key"}, status_code=400)

        # Identify caller (we use user_id if present, else anonymous)
        user_id = getattr(request.state, "user_id", None) or "anon"

        # Read and preserve body (DownstreamClient will use request.state.raw_body)
        body = await request.body()
        request.state.raw_body = body
        req_hash = _sha256_hex(body)

        path = request.url.path
        resp_key = f"idem:resp:{method}:{path}:{user_id}:{idem_key}"
        lock_key = f"idem:lock:{method}:{path}:{user_id}:{idem_key}"

        # 1) If response already stored -> replay
        existing = await r.get(resp_key)
        if existing:
            try:
                data = json.loads(existing)
            except Exception:
                # Corrupt entry: safest is to fail closed for this idempotency key
                return JSONResponse({"error": "idempotency_store_corrupt"}, status_code=503)

            if data.get("req_hash") != req_hash:
                return JSONResponse(
                    {"error": "idempotency_key_conflict", "detail": "same key used with different payload"},
                    status_code=409,
                )

            headers = data.get("headers") or {}
            return Response(
                content=bytes.fromhex(data["body_hex"]), status_code=int(data["status"]), headers=headers
            )

        # 2) Acquire short lock to avoid duplicate in-flight calls
        # NX = only set if not exists; EX = expire
        lock_ok = await r.set(lock_key, "1", ex=30, nx=True)
        if not lock_ok:
            # Another request with same key is running; client should retry after short wait
            return JSONResponse(
                {"error": "idempotency_inflight", "detail": "request with same key is already processing"},
                status_code=409,
                headers={"Retry-After": "2"},
            )

        try:
            # Call downstream (or internal handler) once
            response: Response = await call_next(request)

            # Only store “successful-ish” results. MVP: store any 2xx.
            if 200 <= response.status_code < 300:
                # Read response body safely
                resp_body = b""
                async for chunk in response.body_iterator:
                    resp_body += chunk

                # Minimal headers to replay safely
                replay_headers = {}
                ct = response.headers.get("content-type")
                if ct:
                    replay_headers["content-type"] = ct

                payload = {
                    "status": response.status_code,
                    "headers": replay_headers,
                    "body_hex": resp_body.hex(),
                    "req_hash": req_hash,
                }
                await r.set(resp_key, json.dumps(payload), ex=settings.IDEM_TTL_SECONDS)

                # Return the reconstructed response (since we consumed iterator)
                return Response(content=resp_body, status_code=response.status_code, headers=response.headers)

            return response

        finally:
            # Release lock (ok if already expired)
            try:
                await r.delete(lock_key)
            except Exception:
                pass
