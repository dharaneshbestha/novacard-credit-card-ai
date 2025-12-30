-- Step C7.1.A-3: Enforce the PENDING-first lifecycle

-- Requirement

-- Transactions must start as PENDING, and only transition to:
-- 	•	POSTED
-- 	•	FAILED
-- 	•	DECLINED

-- Expected result

-- You can’t accidentally write weird statuses like “DONE” or “OK”.

-- Approach

-- Add a status CHECK constraint.

-- ⸻

-- Step C7.1.A-4: Idempotency uniqueness

-- Requirement

-- Prevent duplicate transactions for same user_id + idempotency_key.

-- Expected result

-- DB rejects duplicates, enabling safe retries.

-- Approach

-- Add UNIQUE(user_id, idempotency_key).

-- ⸻

-- Step C7.1.A-5: Ledger dedupe (no double posting)

-- Requirement

-- Prevent duplicate ledger postings for the same transaction.

-- Expected result

-- Retries won’t create duplicate ledger rows.

-- Approach

-- Add UNIQUE(transaction_id, entry_index).

-- C7.1.A-3/A-4/A-5 — Hardening constraints + uniqueness

-- A-3: status must be one of known values
ALTER TABLE transactions
  ADD CONSTRAINT chk_transactions_status
  CHECK (status IN ('PENDING', 'POSTED', 'FAILED', 'DECLINED'));

-- A-3 (optional but recommended): txn_type must be known
ALTER TABLE transactions
  ADD CONSTRAINT chk_transactions_type
  CHECK (txn_type IN ('PURCHASE'));

-- A-4: idempotency uniqueness per user
CREATE UNIQUE INDEX IF NOT EXISTS uq_transactions_user_idempotency
  ON transactions (user_id, idempotency_key);

-- A-5: ledger de-dup by transaction + entry index
CREATE UNIQUE INDEX IF NOT EXISTS uq_ledger_transaction_entry_index
  ON ledger_entries (transaction_id, entry_index);