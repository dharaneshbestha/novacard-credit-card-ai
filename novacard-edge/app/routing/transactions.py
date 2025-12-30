from fastapi import APIRouter, Request
from starlette.responses import JSONResponse, Response

from app.clients.downstream import DownstreamClient
from app.config import settings
from app.utils.downstream_errors import DownstreamError
from app.utils.error_mapping import map_downstream_error

router = APIRouter()
ds = DownstreamClient()


def _req_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _as_json_or_text(r) -> any:
    # httpx.Response compatible
    try:
        return r.json()
    except Exception:
        try:
            return r.text
        except Exception:
            return None


@router.api_route("/transactions/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_transactions(request: Request, path: str):
    try:
        # ✅ rewrite /transactions/<path> -> /<path> for downstream
        request.state.forward_path = f"/{path}"

        r = await ds.forward(
            request=request,
            base_url=str(settings.EDGE_TXN_BASE_URL),
            audience="novacard-txn",
            service_name="transaction",
        )
        # ✅ pass-through for success
        if 200 <= r.status_code <= 299:
            return Response(content=r.content, status_code=r.status_code, headers=dict(r.headers))

        # ✅ D3.5: normalize ALL downstream non-2xx into Edge envelope
        detail = _as_json_or_text(r)

        # If your existing error mapper already returns the right envelope, keep using it.
        # But most mappers only handle exceptions, not a plain downstream HTTP response.
        # So we enforce the envelope here.
        return JSONResponse(
            status_code=503 if r.status_code >= 500 else r.status_code,
            content={
                "error": "downstream_error" if r.status_code >= 500 else "downstream_rejected",
                "service": "transaction",
                "detail": detail,
                "request_id": _req_id(request),
            },
            headers={"x-request-id": _req_id(request) or ""},
        )

    except DownstreamError as e:
        resp = map_downstream_error(e)

        # Ensure request_id is present in body (best effort)
        if isinstance(resp, JSONResponse):
            try:
                body = resp.body
                # body is bytes; if you want to strictly enforce request_id, do it inside map_downstream_error()
                # We'll still ensure header is present here:
                resp.headers["x-request-id"] = _req_id(request) or resp.headers.get("x-request-id", "")
            except Exception:
                pass

        return resp
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "error": "downstream_unavailable",
                "service": "transaction",
                "detail": f"{type(e).__name__}: {str(e)}",
                "request_id": _req_id(request),
            },
            headers={"x-request-id": _req_id(request) or ""},
        )
