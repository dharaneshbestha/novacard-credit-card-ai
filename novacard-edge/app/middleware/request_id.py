import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.utils.audit_log import audit_log

REQUEST_ID_HEADER = "X-Request-Id"

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = rid
        audit_log(
            service="edge",
            event="request_start",
            request_id=request.state.request_id,
            path=str(request.url.path),
            method=request.method,
        )
        response: Response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = rid
        return response