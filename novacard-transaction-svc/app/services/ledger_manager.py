from __future__ import annotations

import asyncpg
from dataclasses import dataclass
from uuid import UUID
from app.metrics import snapshot_rebuild_total, snapshot_drift_detected_total


@dataclass(frozen=True)
class PostResult:
    ok: bool
    reason: str | None = None


class LedgerManager:
    def __init__(self, merchant_account_id: UUID):
        self.merchant_account_id = merchant_account_id

    async def post_purchase_atomic(
        self,
        conn: asyncpg.Connection,
        *,
        transaction_id: UUID,
        user_id: str,
        user_account_id: UUID,
        amount_minor: int,
        currency: str,
        service: str = "transaction",
    ) -> PostResult:
        # 0) Validate
        if amount_minor <= 0:
            return PostResult(False, "amount_must_be_positive")

        # 1) Lock account row to prevent double-spend
        acct = await conn.fetchrow(
            """
            SELECT account_id, user_id, status, currency, credit_limit_minor
            FROM accounts
            WHERE account_id=$1 AND user_id=$2
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

        credit_limit = int(acct["credit_limit_minor"])

        # 2) Ensure snapshot exists
        await conn.execute(
            """
            INSERT INTO account_balance_snapshots (account_id, balance_minor)
            VALUES ($1, 0)
            ON CONFLICT (account_id) DO NOTHING
            """,
            user_account_id,
        )

        # 3) Lock snapshot row & read balance
        snap = await conn.fetchrow(
            """
            SELECT account_id, balance_minor
            FROM account_balance_snapshots
            WHERE account_id=$1
            FOR UPDATE
            """,
            user_account_id,
        )

        if not snap:
            # self-heal path
            snapshot_rebuild_total.labels(service=service, reason="missing").inc()

            # create row
            await conn.execute(
                """
                INSERT INTO account_balance_snapshots (account_id, balance_minor)
                VALUES ($1, 0)
                """,
                user_account_id,
            )
            # rebuild from ledger
            await conn.execute(
                """
                UPDATE account_balance_snapshots s
                SET balance_minor = COALESCE(x.balance_minor, 0),
                    updated_at = now()
                FROM (
                    SELECT
                        account_id,
                        SUM(
                            CASE
                                WHEN entry_type='DEBIT'  THEN -amount_minor
                                WHEN entry_type='CREDIT' THEN  amount_minor
                                ELSE 0
                            END
                        ) AS balance_minor
                    FROM ledger_entries
                    WHERE account_id = $1
                    GROUP BY account_id
                ) x
                WHERE s.account_id = $1
                """,
                user_account_id,
            )

            snap = await conn.fetchrow(
                """
                SELECT account_id, balance_minor
                FROM account_balance_snapshots
                WHERE account_id=$1
                FOR UPDATE
                """,
                user_account_id,
            )
            if not snap:
                snapshot_drift_detected_total.labels(service=service, reason="rebuild_failed").inc()
                return PostResult(False, "snapshot_rebuild_failed")

        balance_minor = int(snap["balance_minor"])

        # available = credit_limit + balance (balance negative means spent)
        available = credit_limit + balance_minor
        if amount_minor > available:
            return PostResult(False, "insufficient_credit")

        # 4) Two-leg ledger write
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
                (user_account_id, transaction_id, 0, "DEBIT", currency, amount_minor),
                (self.merchant_account_id, transaction_id, 1, "CREDIT", currency, amount_minor),
            ],
        )

        # 5) Snapshot update (user side)
        new_balance = balance_minor - int(amount_minor)
        await conn.execute(
            """
            UPDATE account_balance_snapshots
            SET balance_minor=$2, updated_at=now()
            WHERE account_id=$1
            """,
            user_account_id,
            new_balance,
        )

        # post-condition drift check
        check = await conn.fetchval(
            "SELECT balance_minor FROM account_balance_snapshots WHERE account_id=$1",
            user_account_id,
        )
        if check is None or int(check) != new_balance:
            snapshot_drift_detected_total.labels(service=service, reason="post_condition_mismatch").inc()

        return PostResult(True, None)