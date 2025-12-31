import asyncpg
from fastapi import APIRouter, Depends

from app.db import get_pool
from app.metrics import snapshot_drift_detected_total

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/drift/check")
async def drift_check(account_id: str, pool: asyncpg.Pool = Depends(get_pool)):
    async with pool.acquire() as conn:
        snap = await conn.fetchval(
            "SELECT balance_minor FROM account_balance_snapshots WHERE account_id=$1::uuid",
            account_id,
        )
        led = await conn.fetchval(
            """
            SELECT COALESCE(SUM(
                CASE
                    WHEN entry_type='DEBIT' THEN -amount_minor
                    WHEN entry_type='CREDIT' THEN  amount_minor
                    ELSE 0
                END
            ),0)
            FROM ledger_entries WHERE account_id=$1::uuid
            """,
            account_id,
        )
        if snap != led:
            snapshot_drift_detected_total.labels(service="transaction", reason="admin_check").inc()
        return {
            "account_id": account_id,
            "snapshot": int(snap or 0),
            "ledger": int(led or 0),
            "match": snap == led,
        }
