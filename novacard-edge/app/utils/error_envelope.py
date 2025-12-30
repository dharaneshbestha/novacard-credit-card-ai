from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


def edge_error(request: Request, *, status_code: int, error: str, service: str, detail: Any):
    rid = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error,
            "service": service,
            "detail": detail,
            "request_id": rid,
        },
    )
