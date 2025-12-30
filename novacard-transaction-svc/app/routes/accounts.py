from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.db import get_pool

router = APIRouter(prefix="/accounts", tags=["accounts"])


class BalanceResponse(BaseModel):
    account_id: str
    user_id: str
    credit_limit_minor: int
    balance_minor: int
    available_minor: int
    snapshot_updated_at: str  # ISO timestamp


@router.get("/{account_id}/balance", response_model=BalanceResponse)
async def get_balance(
    account_id: UUID,
    x_user_id: str = Header(..., alias="X-User-Id"),
):
    pool = await get_pool()
    print(f"DEBUG: Looking for Merchant ID accounts.py: {account_id}")
    print(f"DEBUG: Type of ID: {type(account_id)}")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
              a.account_id::text AS account_id,
              a.user_id,
              a.credit_limit_minor,
              s.balance_minor,
              (a.credit_limit_minor + s.balance_minor) AS available_minor,
              s.updated_at::text AS snapshot_updated_at
            FROM accounts a
            JOIN account_balance_snapshots s ON s.account_id = a.account_id
            WHERE a.account_id=$1 AND a.user_id=$2
            """,
            account_id,
            x_user_id,
        )

    if not row:
        raise HTTPException(status_code=404, detail="account_not_found")

    return BalanceResponse(**dict(row))
