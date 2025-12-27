-- C7.2.2 - Backfill snapshot rows for existing accounts
-- Idempotent: safe to run multiple times

BEGIN;

INSERT INTO account_balance_snapshots (account_id, balance_minor)
SELECT a.account_id, 0
FROM accounts a
LEFT JOIN account_balance_snapshots s ON s.account_id = a.account_id
WHERE s.account_id IS NULL;

COMMIT;

-- Run this command to apply the sql file
--docker compose exec -T postgres psql -U novacard -d novacard -f /dev/stdin < sql/migrations/2025-12-25_02_backfill_account_balance_snapshots.sql