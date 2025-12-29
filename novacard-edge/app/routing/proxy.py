from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from app.clients.downstream import DownstreamClient
from app.config import settings
from app.utils.downstream_error_mapper import map_downstream_error
from app.utils.downstream_errors import DownstreamError

router = APIRouter()
ds = DownstreamClient()

HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "transfer-encoding", "upgrade",
    "server", "date", "content-length",
}

def safe_headers(h: dict) -> dict:
    out = {}
    for k, v in h.items():
        lk = k.lower()
        if lk in HOP_BY_HOP:
            continue
        out[k] = v
    return out

def map_downstream_error(e: DownstreamError) -> JSONResponse:
    status_map = {
        "circuit_open": 503,
        "downstream_timeout": 504,
        "downstream_unreachable": 503,
        "downstream_5xx": 502,
        "downstream_error": 502,
        "config_error": 500,
    }
    status = status_map.get(e.code, 502)

    headers = {}
    if e.code == "circuit_open":
        # default retry-after; also allow parsing from detail if present
        retry_after = "30"
        # optional: if detail is like "retry_after=30" we extract it
        if e.detail and "retry_after=" in e.detail:
            retry_after = e.detail.split("retry_after=", 1)[1].split(",", 1)[0].strip()
        headers["Retry-After"] = retry_after

    return JSONResponse(
        {"error": e.code, "service": e.service, "detail": e.detail},
        status_code=status,
        headers=headers,
    )

@router.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_auth(request: Request, path: str):
    try:
        r = await ds.forward(
            request,
            str(settings.AUTH_BASE_URL),
            audience="novacard-auth",
            service_name="auth",
        )
        return Response(content=r.content, status_code=r.status_code, headers=safe_headers(dict(r.headers)))
    except DownstreamError as e:
        return map_downstream_error(e, request_id=getattr(request.state, "request_id", None))
    except Exception as e:
        return JSONResponse(
            {"error": "downstream_unavailable", "service": "auth", "detail": str(e)},
            status_code=503,
        )


@router.api_route("/users/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_users(request: Request, path: str):
    try:
        r = await ds.forward(
            request,
            str(settings.USER_BASE_URL),
            audience="novacard-user",
            service_name="user",
        )
        return Response(content=r.content, status_code=r.status_code, headers=safe_headers(dict(r.headers)))

    except DownstreamError as e:
        # ✅ Controlled failure response (no 500)
        return map_downstream_error(e, request_id=getattr(request.state, "request_id", None))

    except Exception as e:
        return JSONResponse(
            {"error": "downstream_unavailable", "service": "user", "detail": str(e)},
            status_code=503,
        )


@router.api_route("/kyc/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_kyc(request: Request, path: str, ):
    try:
        r = await ds.forward(request, str(settings.KYC_BASE_URL), audience="novacard-kyc")
        return Response(content=r.content, status_code=r.status_code, headers=safe_headers(dict(r.headers)))
    except DownstreamError as e:
        return map_downstream_error(e, request_id=getattr(request.state, "request_id", None))
    except Exception as e:
        return JSONResponse(
            {"error": "downstream_unavailable", "service": "kyc", "detail": str(e)},
            status_code=503,
        )


@router.api_route("/accounts/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_accounts(request: Request, path: str):
    try:
        r = await ds.forward(
            request,
            str(settings.ACCOUNT_BASE_URL),
            audience="novacard-account",
            service_name="account",
        )
        return Response(content=r.content, status_code=r.status_code, headers=dict(r.headers))
    except DownstreamError as e:
        return map_downstream_error(e)
    except Exception as e:
        return JSONResponse({"error": "downstream_unavailable", "service": "account", "detail": str(e)}, status_code=503)