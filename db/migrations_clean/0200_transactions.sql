-- db/migrations_clean/0200_transactions.sql
CREATE TABLE transactions (
  transaction_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         TEXT NOT NULL,
  account_id      UUID NOT NULL REFERENCES accounts(account_id),
  idempotency_key TEXT NOT NULL,
  txn_type        TEXT NOT NULL, -- PURCHASE (v1)
  currency        CHAR(3) NOT NULL DEFAULT 'USD',
  amount_minor    BIGINT NOT NULL,
  status          TEXT NOT NULL DEFAULT 'PENDING', -- PENDING | POSTED | FAILED | DECLINED
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE transactions
  ADD CONSTRAINT uq_transactions_user_idem UNIQUE (user_id, idempotency_key),
  ADD CONSTRAINT chk_transactions_amount_positive CHECK (amount_minor > 0),
  ADD CONSTRAINT chk_transactions_currency CHECK (currency ~ '^[A-Z]{3}$'),
  ADD CONSTRAINT chk_transactions_status CHECK (status IN ('PENDING','POSTED','FAILED','DECLINED')),
  ADD CONSTRAINT chk_transactions_type CHECK (txn_type IN ('PURCHASE'));

CREATE INDEX idx_transactions_user_created_at ON transactions(user_id, created_at DESC);
CREATE INDEX idx_transactions_account_created_at ON transactions(account_id, created_at DESC);