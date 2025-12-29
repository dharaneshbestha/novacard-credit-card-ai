-- db/migrations_clean/0400_account_balance_snapshots.sql
CREATE TABLE account_balance_snapshots (
  account_id            UUID PRIMARY KEY REFERENCES accounts(account_id),
  balance_minor         BIGINT NOT NULL DEFAULT 0,
  as_of_ledger_entry_id UUID NULL REFERENCES ledger_entries(ledger_entry_id),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_snapshots_updated_at ON account_balance_snapshots(updated_at DESC);