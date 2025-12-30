-- C7.2.2 - Backfill snapshot rows for existing accounts
-- Idempotent: safe to run multiple times

BEGIN;

-- Ensure snapshot rows exist for every account
INSERT INTO account_balance_snapshots (account_id, balance_minor, updated_at)
SELECT a.account_id, 0, now()
FROM accounts a
ON CONFLICT (account_id) DO NOTHING;

-- Recompute from ledger for every account
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
  GROUP BY account_id
) x
WHERE s.account_id = x.account_id;

COMMIT;


-- Run this command to apply the sql file
--docker compose exec -T postgres psql -U novacard -d novacard -f /dev/stdin < sql/migrations/2025-12-25_02_backfill_account_balance_snapshots.sql