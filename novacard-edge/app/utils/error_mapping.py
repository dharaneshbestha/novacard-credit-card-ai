from starlette.responses import JSONResponse

from app.utils.downstream_errors import DownstreamError


def map_downstream_error(e: DownstreamError) -> JSONResponse:
    """
    Maps downstream service failures into stable Edge responses.
    Never leak internal exceptions or stack traces.
    """

    if e.code == "circuit_open":
        return JSONResponse(
            {
                "error": "service_temporarily_unavailable",
                "service": e.service,
                "detail": e.detail,
            },
            status_code=503,
        )

    if e.code == "downstream_timeout":
        return JSONResponse(
            {
                "error": "downstream_timeout",
                "service": e.service,
                "detail": e.detail,
            },
            status_code=504,
        )

    if e.code == "downstream_unreachable":
        return JSONResponse(
            {
                "error": "downstream_unavailable",
                "service": e.service,
                "detail": e.detail,
            },
            status_code=503,
        )

    if e.code == "downstream_5xx":
        return JSONResponse(
            {
                "error": "downstream_error",
                "service": e.service,
                "detail": e.detail,
            },
            status_code=502,
        )

    if e.code == "config_error":
        return JSONResponse(
            {
                "error": "service_misconfigured",
                "service": e.service,
                "detail": e.detail,
            },
            status_code=500,
        )

    # Fallback (never expose internals)
    return JSONResponse(
        {
            "error": "downstream_failure",
            "service": e.service,
        },
        status_code=502,
    )
