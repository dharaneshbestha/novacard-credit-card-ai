from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4

import asyncpg
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.db import get_pool  # adjust if needed
from app.services.idempotency import (
    idem_get_final,
    idem_try_lock,
    idem_set_final,
    IdemInProgress,
)
from app.services.ledger_manager import LedgerManager, PostResult  # adjust if needed

router = APIRouter(prefix="/purchase", tags=["purchase"])


class PurchaseRequest(BaseModel):
    amount_minor: int = Field(..., gt=0)
    currency: str = Field("USD", min_length=3, max_length=3)


class PurchaseResponse(BaseModel):
    status: str
    transaction_id: str
    reason: str


def _get_user_id(request: Request) -> str:
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="missing_user_context")
    return str(user_id)


async def _get_user_account_id(conn: asyncpg.Connection, user_id: str) -> UUID:
    row = await conn.fetchrow(
        """
        SELECT account_id
        FROM accounts
        WHERE user_id=$1 AND status='ACTIVE'
        ORDER BY created_at ASC
        LIMIT 1
        """,
        user_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="account_not_found")
    return UUID(str(row["account_id"]))


@router.post("", response_model=PurchaseResponse)
async def purchase(
    request: Request,
    payload: PurchaseRequest,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    pool: asyncpg.Pool = Depends(get_pool),
):
    """
    POST /purchase
    Requires:
      - request.state.user_id set by UserAuth middleware
      - Idempotency-Key header
    """

    user_id = _get_user_id(request)

    idem_key = (idempotency_key or "").strip()
    if not idem_key:
        raise HTTPException(status_code=400, detail="missing_idempotency_key")

    # 1) Return final if exists
    cached = await idem_get_final(user_id, idem_key)
    if cached:
        return JSONResponse(cached, status_code=200)

    # 2) Acquire in-progress lock (NX). If fails -> 409
    try:
        await idem_try_lock(user_id, idem_key)
    except IdemInProgress:
        return JSONResponse(
            {"status": "PENDING", "transaction_id": "", "reason": "idempotency_in_progress"},
            status_code=409,
        )

    # 3) Perform atomic DB work
    transaction_id = uuid4()

    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                user_account_id = await _get_user_account_id(conn, user_id)

                # ✅ Insert transaction row FIRST (satisfies FK for ledger_entries)
                await conn.execute(
                    """
                    INSERT INTO transactions (
                        transaction_id,
                        user_id,
                        account_id,
                        idempotency_key,
                        txn_type,
                        currency,
                        amount_minor,
                        status
                    )
                    VALUES ($1,$2,$3,$4,$5,$6,$7,'PENDING')
                    """,
                    transaction_id,
                    user_id,
                    user_account_id,
                    idem_key,
                    "PURCHASE",
                    payload.currency,
                    int(payload.amount_minor),
                )

                lm = LedgerManager(merchant_account_id=UUID(str(settings.MERCHANT_ACCOUNT_ID)))

                result: PostResult = await lm.post_purchase_atomic(
                    conn,
                    transaction_id=transaction_id,
                    user_id=user_id,
                    user_account_id=user_account_id,
                    amount_minor=int(payload.amount_minor),
                    currency=payload.currency,
                )

                if not result.ok:
                    # Mark FAILED/DECLINED (still inside same DB transaction)
                    await conn.execute(
                        "UPDATE transactions SET status='DECLINED' WHERE transaction_id=$1",
                        transaction_id,
                    )

                    resp = {
                        "status": "DECLINED",
                        "transaction_id": str(transaction_id),
                        "reason": result.reason or "declined",
                    }
                    await idem_set_final(user_id, idem_key, resp)
                    return JSONResponse(resp, status_code=402)

                # Success -> POSTED
                await conn.execute(
                    "UPDATE transactions SET status='POSTED' WHERE transaction_id=$1",
                    transaction_id,
                )

                resp = {
                    "status": "POSTED",
                    "transaction_id": str(transaction_id),
                    "reason": "posted",
                }
                await idem_set_final(user_id, idem_key, resp)
                return JSONResponse(resp, status_code=200)

    except Exception as e:
        # IMPORTANT: fail-safe final response so callers don't get stuck in 409 forever
        resp = {
            "status": "FAILED",
            "transaction_id": str(transaction_id),
            "reason": f"internal_error:{type(e).__name__}",
        }
        try:
            await idem_set_final(user_id, idem_key, resp)
        except Exception:
            # If Redis is down too, still return a deterministic failure
            pass
        return JSONResponse(resp, status_code=500)