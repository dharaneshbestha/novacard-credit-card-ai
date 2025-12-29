from fastapi import APIRouter, Header, HTTPException

from app.db import get_pool

router = APIRouter(prefix="/accounts", tags=["accounts"])

@router.get("")
async def list_accounts(x_user_id: str | None = Header(default=None, alias="X-User-Id")):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="missing X-User-Id")

    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT account_id::text, user_id, account_type, currency, status, credit_limit_minor, created_at
        FROM accounts
        WHERE user_id = $1
        ORDER BY created_at DESC
        """,
        x_user_id,
    )
    return {"accounts": [dict(r) for r in rows]}

@router.get("/{account_id}")
async def get_account(account_id: str, x_user_id: str | None = Header(default=None, alias="X-User-Id")):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="missing X-User-Id")

    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT account_id::text, user_id, account_type, currency, status, credit_limit_minor, created_at
        FROM accounts
        WHERE account_id = $1::uuid AND user_id = $2
        """,
        account_id, x_user_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="account not found")
    return dict(row)