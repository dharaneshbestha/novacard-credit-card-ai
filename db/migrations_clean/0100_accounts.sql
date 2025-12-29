-- db/migrations_clean/0100_accounts.sql
CREATE TABLE accounts (
  account_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id            TEXT NOT NULL,
  account_type       TEXT NOT NULL,     -- USER | MERCHANT | SYSTEM
  currency           CHAR(3) NOT NULL DEFAULT 'USD',
  status             TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE | SUSPENDED | CLOSED
  credit_limit_minor BIGINT NOT NULL DEFAULT 0,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- minimal checks
ALTER TABLE accounts
  ADD CONSTRAINT chk_accounts_currency CHECK (currency ~ '^[A-Z]{3}$'),
  ADD CONSTRAINT chk_accounts_status CHECK (status IN ('ACTIVE','SUSPENDED','CLOSED')),
  ADD CONSTRAINT chk_accounts_type CHECK (account_type IN ('USER','MERCHANT','SYSTEM')),
  ADD CONSTRAINT chk_accounts_credit_limit_nonneg CHECK (credit_limit_minor >= 0);

CREATE INDEX idx_accounts_user_id ON accounts(user_id);
CREATE INDEX idx_accounts_type ON accounts(account_type);