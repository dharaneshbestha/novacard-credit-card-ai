-- C7.2.1 - Balance Snapshot Table
-- Idempotent migration (safe to run multiple times)

BEGIN;

CREATE TABLE IF NOT EXISTS account_balance_snapshots (
  account_id uuid PRIMARY KEY REFERENCES accounts(account_id),
  balance_minor bigint NOT NULL DEFAULT 0,
  as_of_ledger_entry_id uuid NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Optional: keep updated_at current via application logic (preferred for simplicity)
-- If you want a DB trigger later, we can add it in another migration.

COMMIT;

-- Run this command to apply the sql file
--docker compose exec -T postgres psql -U novacard -d novacard -f /dev/stdin < sql/migrations/2025-12-25_01_create_account_balance_snapshots.sql