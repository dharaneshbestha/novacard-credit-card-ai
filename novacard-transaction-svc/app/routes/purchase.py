from __future__ import annotations

import traceback
from contextlib import suppress
from uuid import UUID, uuid4

import asyncpg
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from app.utils.audit_log import audit_log
from app.config import settings
from app.db import get_pool
from app.services.idempotency import (
    IdemInProgress,
    idem_get_final,
    idem_set_final,
    idem_try_lock,
)
from app.services.ledger_manager import LedgerManager

router = APIRouter(prefix="/purchase", tags=["purchase"])


class PurchaseRequest(BaseModel):
    amount_minor: int = Field(..., gt=0)
    currency: str = Field("USD", min_length=3, max_length=3)


class PurchaseResponse(BaseModel):
    status: str
    transaction_id: str
    reason: str


def _as_uuid(x) -> UUID:
    """Accept UUID or UUID-like string and return UUID."""
    if isinstance(x, UUID):
        return x
    return UUID(str(x))


def _get_user_id(request: Request) -> str:
    user_id = getattr(request.state, "user_id", None)
    print("user_id =", user_id)
    if not user_id:
        raise HTTPException(status_code=401, detail="missing_user_context")
    return str(user_id)


async def _get_user_account_id(conn: asyncpg.Connection, user_id: str) -> UUID:
    print(f"DEBUG: Looking for User ID: {user_id}")
    print(f"DEBUG: Type of ID: {type(user_id)}")

    row = await conn.fetchrow(
        """
        SELECT account_id
        FROM accounts
        WHERE user_id=$1 AND status='ACTIVE' AND account_type='USER'
        ORDER BY created_at ASC
        LIMIT 1
        """,
        user_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="account_not_found")
    return _as_uuid(row["account_id"])


async def _assert_merchant_account(conn: asyncpg.Connection, merchant_account_id: UUID) -> None:
    row = await conn.fetchrow(
        """
        SELECT account_id, account_type, status, currency
        FROM accounts
        WHERE account_id=$1
        """,
        merchant_account_id,
    )
    if not row:
        raise HTTPException(status_code=500, detail="merchant_account_missing")
    if row["account_type"] != "MERCHANT":
        raise HTTPException(status_code=500, detail="merchant_account_wrong_type")
    if row["status"] != "ACTIVE":
        raise HTTPException(status_code=500, detail="merchant_account_inactive")


@router.post("", response_model=PurchaseResponse)
async def purchase(
    request: Request,
    payload: PurchaseRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    pool: asyncpg.Pool = Depends(get_pool),
):
    user_id = _get_user_id(request)
    rid = getattr(request.state, "request_id", None)
    idem_key = (idempotency_key or "").strip()
    if not idem_key:
        raise HTTPException(status_code=400, detail="missing_idempotency_key")

    # 1) Final cache hit (fast path)
    cached = await idem_get_final(user_id, idem_key)
    if cached:
        return JSONResponse(cached, status_code=200)

    # 2) Acquire idempotency lock
    try:
        await idem_try_lock(user_id, idem_key)
    except IdemInProgress:
        audit_log(
            service="transaction-svc",
            event="idempotency_in_progress",
            request_id=rid,
            user_id=user_id,
            path=request.url.path,
            method=request.method,
            status_code=409,
            detail="idempotency_in_progress",
        )
        return JSONResponse(
            {"status": "PENDING", "transaction_id": "", "reason": "idempotency_in_progress"},
            status_code=409,
        )

    transaction_id = uuid4()

    # ✅ Convert merchant ID ONCE to UUID
    try:
        merchant_account_id = _as_uuid(settings.MERCHANT_ACCOUNT_ID)
    except Exception as e:
        # This is a config error, fail fast and release idem lock via final
        resp = {
            "status": "FAILED",
            "transaction_id": str(transaction_id),
            "reason": f"config_error:bad_merchant_account_id:{type(e).__name__}",
        }
        audit_log(
            service="transaction-svc",
            event="purchase_failed",
            request_id=rid,
            user_id=user_id,
            path=request.url.path,
            method=request.method,
            status_code=500,
            detail="config_error:bad_merchant_account_id",
        )
        with suppress(Exception):
            await idem_set_final(user_id, idem_key, resp)
        return JSONResponse(resp, status_code=500)

    print(f"DEBUG: Looking for Merchant ID purchase.py: {merchant_account_id}")
    print(f"DEBUG: Type of ID: {type(merchant_account_id)}")

    resp: dict = {}
    http_status: int = 500

    try:
        async with pool.acquire() as conn, conn.transaction():
            # Ensure merchant/system account exists and is correct
            await _assert_merchant_account(conn, merchant_account_id)

            user_account_id = await _get_user_account_id(conn, user_id)

            # Create transaction row FIRST to satisfy FK from ledger_entries
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
                VALUES ($1,$2,$3,$4,'PURCHASE',$5,$6,'PENDING')
                """,
                transaction_id,
                user_id,
                user_account_id,
                idem_key,
                payload.currency,
                int(payload.amount_minor),
            )

            print(f"DEBUG: Merchant ID insert-purchase.py: {merchant_account_id}")
            print(f"DEBUG: Type of merchant ID: {type(merchant_account_id)}")

            lm = LedgerManager(merchant_account_id=merchant_account_id)

            result = await lm.post_purchase_atomic(
                conn,
                transaction_id=transaction_id,
                user_id=user_id,
                user_account_id=user_account_id,
                amount_minor=int(payload.amount_minor),
                currency=payload.currency,
                idempotency_key=idem_key,
            )

            if not result.ok:
                await conn.execute(
                    "UPDATE transactions SET status='DECLINED' WHERE transaction_id=$1",
                    transaction_id,
                )
                resp = {
                    "status": "DECLINED",
                    "transaction_id": str(transaction_id),
                    "reason": result.reason or "declined",
                }
                audit_log(
                    service="transaction-svc",
                    event="purchase_declined",
                    request_id=rid,
                    user_id=user_id,
                    path=request.url.path,
                    method=request.method,
                    status_code=402,
                    detail="declined",
                )
                http_status = 402
            else:
                await conn.execute(
                    "UPDATE transactions SET status='POSTED' WHERE transaction_id=$1",
                    transaction_id,
                )
                resp = {
                    "status": "POSTED",
                    "transaction_id": str(transaction_id),
                    "reason": "posted",
                }
                audit_log(
                    service="transaction-svc",
                    event="purchase_posted",
                    request_id=rid,
                    user_id=user_id,
                    path=request.url.path,
                    method=request.method,
                    status_code=200,
                    detail="posted",
                )
                http_status = 200

        # DB committed successfully -> now write idempotency final
        await idem_set_final(user_id, idem_key, resp)
        return JSONResponse(resp, status_code=http_status)

    except HTTPException as e:
        resp = {
            "status": "FAILED",
            "transaction_id": str(transaction_id),
            "reason": f"http_{e.status_code}:{e.detail}",
        }
        audit_log(
            service="transaction-svc",
            event="purchase_failed",
            request_id=rid,
            user_id=user_id,
            path=request.url.path,
            method=request.method,
            status_code=http_status,
            detail=f"http_{e.status_code}:{e.detail}",
        )
        http_status = 500 if e.status_code >= 500 else e.status_code
        with suppress(Exception):
            await idem_set_final(user_id, idem_key, resp)
        return JSONResponse(resp, status_code=http_status)

    except asyncpg.ForeignKeyViolationError:
        resp = {
            "status": "FAILED",
            "transaction_id": str(transaction_id),
            "reason": "internal_error:ForeignKeyViolationError",
        }
        audit_log(
            service="transaction-svc",
            event="purchase_failed",
            request_id=rid,
            user_id=user_id,
            path=request.url.path,
            method=request.method,
            status_code=http_status,
            detail=f"http_{e.status_code}:{e.detail}",
        )
        with suppress(Exception):
            await idem_set_final(user_id, idem_key, resp)
        return JSONResponse(resp, status_code=500)

    except Exception as e:
        # ✅ print the traceback so you can see the real bug next time
        print("PURCHASE FAILED:", repr(e))
        print(traceback.format_exc())

        resp = {
            "status": "FAILED",
            "transaction_id": str(transaction_id),
            "reason": f"internal_error:{type(e).__name__}",
        }
        audit_log(
            service="transaction-svc",
            event="purchase_failed",
            request_id=rid,
            user_id=user_id,
            path=request.url.path,
            method=request.method,
            status_code=http_status,
            detail=f"http_{e.status_code}:{e.detail}",
        )
        with suppress(Exception):
            await idem_set_final(user_id, idem_key, resp)
        return JSONResponse(resp, status_code=500)
