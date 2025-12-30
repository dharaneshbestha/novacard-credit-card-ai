-- C7.1.A-1 — Core schema (v1)
-- Assumes PostgreSQL 13+.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ----------------------------
-- accounts
-- ----------------------------
CREATE TABLE IF NOT EXISTS accounts (
  account_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      TEXT NOT NULL,
  account_type TEXT NOT NULL,                 -- e.g. "CREDIT"
  currency     CHAR(3) NOT NULL DEFAULT 'USD',
  status       TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE | SUSPENDED | CLOSED
  credit_limit_minor BIGINT NOT NULL DEFAULT 0,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ----------------------------
-- transactions
-- ----------------------------
CREATE TABLE IF NOT EXISTS transactions (
  transaction_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          TEXT NOT NULL,
  account_id       UUID NOT NULL REFERENCES accounts(account_id),
  idempotency_key  TEXT NOT NULL,
  txn_type         TEXT NOT NULL,   -- PURCHASE (v1). Later PAYMENT/REFUND/CHARGEBACK
  currency         CHAR(3) NOT NULL DEFAULT 'USD',
  amount_minor     BIGINT NOT NULL,
  status           TEXT NOT NULL DEFAULT 'PENDING', -- PENDING | POSTED | FAILED | DECLINED
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ----------------------------
-- ledger_entries (append-only)
-- ----------------------------
CREATE TABLE IF NOT EXISTS ledger_entries (
  ledger_entry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id      UUID NOT NULL REFERENCES accounts(account_id),
  transaction_id  UUID NOT NULL REFERENCES transactions(transaction_id),
  entry_index     INT NOT NULL DEFAULT 0,     -- v1 single entry; v2 supports multiple
  entry_type      TEXT NOT NULL,              -- DEBIT | CREDIT
  currency        CHAR(3) NOT NULL DEFAULT 'USD',
  amount_minor    BIGINT NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- db/migrations_clean/0400_account_balance_snapshots.sql
CREATE TABLE account_balance_snapshots (
  account_id            UUID PRIMARY KEY REFERENCES accounts(account_id),
  balance_minor         BIGINT NOT NULL DEFAULT 0,
  as_of_ledger_entry_id UUID NULL REFERENCES ledger_entries(ledger_entry_id),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_snapshots_updated_at ON account_balance_snapshots(updated_at DESC);