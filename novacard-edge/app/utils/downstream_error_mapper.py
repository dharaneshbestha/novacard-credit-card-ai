from __future__ import annotations

from starlette.responses import JSONResponse

from app.utils.downstream_errors import DownstreamError

RETRYABLE_CODES = {
    "downstream_timeout",
    "downstream_unreachable",
    "circuit_open",
    "downstream_error",
    "downstream_unavailable",
}

NON_RETRYABLE_CODES = {
    "invalid_service_token",
    "missing_service_token",
    "config_error",
    "downstream_4xx",
}


def map_downstream_error(e: DownstreamError, request_id: str | None = None):
    retryable = e.code in RETRYABLE_CODES and e.code not in NON_RETRYABLE_CODES

    # 401/403 should pass through when we *know* it's auth
    if e.code in {"invalid_service_token", "missing_service_token"}:
        status = 401
    # 4xx from downstream (other than auth) – client error
    elif e.code == "downstream_4xx":
        status = 400
    # retryable infra failures
    elif retryable:
        status = 503
    else:
        status = 502

    body = {
        "error": e.code,
        "service": e.service,
        "retryable": retryable,
        "detail": e.detail,
        "request_id": request_id,
    }

    # optional if your DownstreamError carries circuit_state
    circuit_state = getattr(e, "circuit_state", None)
    if circuit_state:
        body["circuit_state"] = circuit_state

    return JSONResponse(body, status_code=status)