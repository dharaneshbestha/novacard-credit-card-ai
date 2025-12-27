from fastapi import APIRouter, Request
from starlette.responses import Response, JSONResponse

from app.clients.downstream import DownstreamClient
from app.utils.downstream_errors import DownstreamError
from app.utils.error_mapping import map_downstream_error
from app.config import settings

router = APIRouter()
ds = DownstreamClient()

@router.api_route("/transactions/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE"])
async def proxy_transactions(request: Request, path: str):
    try:
        # ✅ rewrite /transactions/<path> -> /<path> for downstream
        request.state.forward_path = f"/{path}"

        r = await ds.forward(
            request=request,
            base_url=str(settings.TXN_BASE_URL),
            audience="novacard-txn",
            service_name="transaction",
        )
        return Response(content=r.content, status_code=r.status_code, headers=dict(r.headers))

    except DownstreamError as e:
        return map_downstream_error(e)
    except Exception as e:
        return JSONResponse({"error": "downstream_unavailable", "service": "transaction", "detail": str(e)}, status_code=503)