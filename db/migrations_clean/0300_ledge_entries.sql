-- db/migrations_clean/0300_ledger_entries.sql
CREATE TABLE ledger_entries (
  ledger_entry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id      UUID NOT NULL REFERENCES accounts(account_id),
  transaction_id  UUID NOT NULL REFERENCES transactions(transaction_id),
  entry_index     INTEGER NOT NULL DEFAULT 0,
  entry_type      TEXT NOT NULL, -- DEBIT | CREDIT
  currency        CHAR(3) NOT NULL DEFAULT 'USD',
  amount_minor    BIGINT NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE ledger_entries
  ADD CONSTRAINT chk_ledger_entry_type CHECK (entry_type IN ('DEBIT','CREDIT')),
  ADD CONSTRAINT chk_ledger_amount_positive CHECK (amount_minor > 0),
  ADD CONSTRAINT chk_ledger_currency CHECK (currency ~ '^[A-Z]{3}$'),
  ADD CONSTRAINT uq_ledger_txn_entry_index UNIQUE (transaction_id, entry_index);

CREATE INDEX idx_ledger_account_created_at ON ledger_entries(account_id, created_at DESC);
CREATE INDEX idx_ledger_txn_id ON ledger_entries(transaction_id);