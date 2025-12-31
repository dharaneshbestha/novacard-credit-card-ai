from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from app.utils.audit_log import audit_log  # if you have it; otherwise replace with print/json log


def _rid(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


async def unhandled_exception_handler(request: Request, exc: Exception):
    # Log once, return safe payload
    audit_log(
        service=getattr(request.app.state, "service_name", "unknown"),
        event="unhandled_exception",
        request_id=_rid(request),
        path=request.url.path,
        method=request.method,
        detail=f"{type(exc).__name__}:{str(exc)}",
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "detail": "unhandled_exception",
            "request_id": _rid(request),
        },
    )
