-- C7.2.1 - Balance Snapshot Table
-- Idempotent migration (safe to run multiple times)

-- C7.2.1 - Balance Snapshot Table
-- Idempotent migration (safe to run multiple times)

BEGIN;

CREATE TABLE IF NOT EXISTS account_balance_snapshots (
  account_id UUID PRIMARY KEY REFERENCES accounts(account_id),
  balance_minor BIGINT NOT NULL DEFAULT 0,
  as_of_ledger_entry_id UUID NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Optional: You might want to seed the snapshots for existing accounts
INSERT INTO account_balance_snapshots (account_id, balance_minor)
SELECT account_id, 0 FROM accounts
ON CONFLICT (account_id) DO NOTHING;

COMMIT;
-- Run this command to apply the sql file
--docker compose exec -T postgres psql -U novacard -d novacard -f /dev/stdin < sql/migrations/2025-12-25_01_create_account_balance_snapshots.sql