from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.services.snapshot_rebuild import rebuild_snapshot_for_account

router = APIRouter(prefix="/admin/snapshots", tags=["admin"])


@router.post("/rebuild/{account_id}")
async def rebuild_snapshot(account_id: UUID):
    # For now: local/dev admin. In production, protect with service-to-service auth.
    return await rebuild_snapshot_for_account(account_id, reason="manual")
