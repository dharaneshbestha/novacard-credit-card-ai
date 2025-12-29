-- C7.1.A-6 — Add indexes for fast reads

-- Requirement

-- Keep these queries fast as data grows:
-- 	•	Ledger history by account (most common)
-- 	•	Ledger lookup by transaction
-- 	•	Transaction history by user
-- 	•	Transaction lookup by account

-- Expected Result

-- Common reads don’t degrade as ledger_entries grows.

-- Approach

-- Create targeted B-tree indexes.

-- C7.1.A-6 — Indexes

-- Fast account ledger history (ORDER BY created_at DESC)
CREATE INDEX IF NOT EXISTS idx_ledger_account_created_at
  ON ledger_entries (account_id, created_at DESC);

-- Fast lookup of ledger entries by transaction (for dedupe/debug/audit)
CREATE INDEX IF NOT EXISTS idx_ledger_transaction
  ON ledger_entries (transaction_id);

-- Fast user transaction history
CREATE INDEX IF NOT EXISTS idx_transactions_user_created_at
  ON transactions (user_id, created_at DESC);

-- Fast transaction lookup by account
CREATE INDEX IF NOT EXISTS idx_transactions_account_created_at
  ON transactions (account_id, created_at DESC);