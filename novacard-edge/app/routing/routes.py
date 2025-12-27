from fastapi import APIRouter
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "ok"}

@router.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@router.get("/ready")
async def ready():
    # later: check Redis, downstream reachability, etc.
    return {"status": "ready"}