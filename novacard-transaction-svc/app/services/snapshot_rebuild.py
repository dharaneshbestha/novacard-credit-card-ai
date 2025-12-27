from __future__ import annotations

import asyncpg
from uuid import UUID
from app.metrics import snapshot_rebuild_total


async def rebuild_snapshot_for_account(conn: asyncpg.Connection, account_id: UUID, *, service: str = "transaction") -> None:
    """
    Rebuild snapshot from authoritative ledger. Must be called inside an open DB transaction.
    """
    snapshot_rebuild_total.labels(service=service, reason="manual_rebuild").inc()

    await conn.execute(
        """
        INSERT INTO account_balance_snapshots (account_id, balance_minor)
        VALUES ($1, 0)
        ON CONFLICT (account_id) DO NOTHING
        """,
        account_id,
    )

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
        account_id,
    )