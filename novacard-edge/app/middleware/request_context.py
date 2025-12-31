from __future__ import annotations

import json
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQ_ID_HEADER = "X-Request-Id"


def _now_ts() -> int:
    return int(time.time())


def _log(obj: dict) -> None:
    print(json.dumps(obj, separators=(",", ":"), ensure_ascii=False))


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, service: str):
        super().__init__(app)
        self.service = service

    async def dispatch(self, request: Request, call_next):
        # ALWAYS set request_id before anything else
        rid = request.headers.get(REQ_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = rid

        start = time.perf_counter()

        _log(
            {
                "ts": _now_ts(),
                "service": self.service,
                "event": "request_start",
                "request_id": rid,
                "path": request.url.path,
                "method": request.method,
            }
        )

        try:
            response: Response = await call_next(request)
            dur_ms = int((time.perf_counter() - start) * 1000)

            response.headers[REQ_ID_HEADER] = rid

            _log(
                {
                    "ts": _now_ts(),
                    "service": self.service,
                    "event": "request_end",
                    "request_id": rid,
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": response.status_code,
                    "latency_ms": dur_ms,
                }
            )
            return response

        except Exception as e:
            dur_ms = int((time.perf_counter() - start) * 1000)

            _log(
                {
                    "ts": _now_ts(),
                    "service": self.service,
                    "event": "request_exception",
                    "request_id": rid,
                    "path": request.url.path,
                    "method": request.method,
                    "latency_ms": dur_ms,
                    "error_type": type(e).__name__,
                    "detail": str(e),
                }
            )
            raise
