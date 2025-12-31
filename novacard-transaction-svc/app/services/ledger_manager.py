from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import asyncpg


@dataclass(frozen=True)
class PostResult:
    ok: bool
    reason: str | None = None


class LedgerManager:
    """
    Pattern A (Shared DB, single Unit-of-Work):

    This class guarantees FK correctness by:
    1) inserting the transaction row FIRST (PENDING) for the provided transaction_id
    2) inserting the 2-leg ledger entries referencing that transaction_id
    3) updating snapshots + marking transaction POSTED (or DECLINED)
    """

    def __init__(self, *, merchant_account_id: UUID):
        self.merchant_account_id = merchant_account_id

    async def post_purchase_atomic(
        self,
        conn: asyncpg.Connection,
        *,
        transaction_id: UUID,
        user_id: str,
        user_account_id: UUID,
        idempotency_key: str,
        amount_minor: int,
        currency: str,
    ) -> PostResult:
        # ---------- 0) Basic validation ----------
        if amount_minor <= 0:
            return PostResult(False, "amount_must_be_positive")

        # ---------- 1) Lock USER account row (prevents race / double-spend) ----------
        acct = await conn.fetchrow(
            """
            SELECT account_id, user_id, status, currency, credit_limit_minor
            FROM accounts
            WHERE account_id=$1 AND user_id=$2 AND account_type='USER'
            FOR UPDATE
            """,
            user_account_id,
            user_id,
        )
        if not acct:
            return PostResult(False, "account_not_found")
        if acct["status"] != "ACTIVE":
            return PostResult(False, f"account_status={acct['status']}")
        if currency != acct["currency"]:
            return PostResult(False, "currency_mismatch")

        # ---------- 2) Lock MERCHANT account row (must exist) ----------
        print(f"DEBUG: Looking for Merchant ID ledger_manager.py: {self.merchant_account_id}")
        print(f"DEBUG: Type of ID: {type(self.merchant_account_id)}")
        merch = await conn.fetchrow(
            """
            SELECT account_id, status, currency
            FROM accounts
            WHERE account_id=$1 AND account_type IN ('MERCHANT','SYSTEM')
            FOR UPDATE
            """,
            self.merchant_account_id,
        )
        if not merch:
            return PostResult(False, "merchant_account_not_found")
        if merch["status"] != "ACTIVE":
            return PostResult(False, f"merchant_account_status={merch['status']}")
        if currency != merch["currency"]:
            return PostResult(False, "merchant_currency_mismatch")

        # ---------- 3) Create transaction row FIRST (FK guarantee) ----------
        # If it already exists (rare), that's ok; we just ensure it exists before ledger writes.
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
            ON CONFLICT (transaction_id) DO NOTHING
            """,
            transaction_id,
            user_id,
            user_account_id,
            idempotency_key,
            currency,
            int(amount_minor),
        )

        # Optional: strict check (useful for debugging)
        exists = await conn.fetchval(
            "SELECT 1 FROM transactions WHERE transaction_id=$1",
            transaction_id,
        )
        if not exists:
            return PostResult(False, "missing_transaction_row_for_fk")

        # ---------- 4) Snapshot rows (defensive) ----------
        # user snapshot
        await conn.execute(
            """
            INSERT INTO account_balance_snapshots (account_id, balance_minor)
            VALUES ($1, 0)
            ON CONFLICT (account_id) DO NOTHING
            """,
            user_account_id,
        )
        # merchant snapshot
        await conn.execute(
            """
            INSERT INTO account_balance_snapshots (account_id, balance_minor)
            VALUES ($1, 0)
            ON CONFLICT (account_id) DO NOTHING
            """,
            self.merchant_account_id,
        )

        # lock snapshots
        user_snap = await conn.fetchrow(
            """
            SELECT account_id, balance_minor
            FROM account_balance_snapshots
            WHERE account_id=$1
            FOR UPDATE
            """,
            user_account_id,
        )
        merch_snap = await conn.fetchrow(
            """
            SELECT account_id, balance_minor
            FROM account_balance_snapshots
            WHERE account_id=$1
            FOR UPDATE
            """,
            self.merchant_account_id,
        )
        if not user_snap or not merch_snap:
            return PostResult(False, "snapshot_missing")

        user_balance = int(user_snap["balance_minor"])
        credit_limit = int(acct["credit_limit_minor"])

        available = credit_limit + user_balance  # user_balance is negative when spent
        if amount_minor > available:
            await conn.execute(
                "UPDATE transactions SET status='DECLINED' WHERE transaction_id=$1",
                transaction_id,
            )
            return PostResult(False, "insufficient_credit")

        # ---------- 5) Insert two-leg ledger entries ----------
        # IMPORTANT: transaction row already exists, so FK cannot fail now unless transaction_id differs.
        await conn.executemany(
            """
            INSERT INTO ledger_entries (
                account_id,
                transaction_id,
                entry_index,
                entry_type,
                currency,
                amount_minor
            )
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            [
                (user_account_id, transaction_id, 0, "DEBIT", currency, int(amount_minor)),
                (self.merchant_account_id, transaction_id, 1, "CREDIT", currency, int(amount_minor)),
            ],
        )

        # ---------- 6) Update snapshots atomically ----------
        new_user_balance = user_balance - int(amount_minor)
        new_merch_balance = int(merch_snap["balance_minor"]) + int(amount_minor)

        await conn.execute(
            """
            UPDATE account_balance_snapshots
            SET balance_minor=$2, updated_at=now()
            WHERE account_id=$1
            """,
            user_account_id,
            new_user_balance,
        )
        await conn.execute(
            """
            UPDATE account_balance_snapshots
            SET balance_minor=$2, updated_at=now()
            WHERE account_id=$1
            """,
            self.merchant_account_id,
            new_merch_balance,
        )

        # ---------- 7) Mark transaction POSTED ----------
        await conn.execute(
            "UPDATE transactions SET status='POSTED' WHERE transaction_id=$1",
            transaction_id,
        )

        return PostResult(True, None)
