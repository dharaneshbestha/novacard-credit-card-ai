-- Requirement
-- 	•	Ledger entries must never allow amount_minor <= 0
-- 	•	Transactions must never allow amount_minor <= 0
-- 	•	Currency must be valid 3-letter uppercase (USD/EUR/INR…)

-- Expected Result

-- Bad inserts fail at the DB level (even if a bug slips into API code).

-- Approach

-- Add CHECK constraints with ALTER TABLE.

-- C7.1.A-2 — Constraints

-- Transactions: positive amount
ALTER TABLE transactions
  ADD CONSTRAINT chk_transactions_amount_positive
  CHECK (amount_minor > 0);

-- Ledger: positive amount
ALTER TABLE ledger_entries
  ADD CONSTRAINT chk_ledger_amount_positive
  CHECK (amount_minor > 0);

-- Currency validation: exactly 3 uppercase letters
ALTER TABLE accounts
  ADD CONSTRAINT chk_accounts_currency
  CHECK (currency ~ '^[A-Z]{3}$');

ALTER TABLE transactions
  ADD CONSTRAINT chk_transactions_currency
  CHECK (currency ~ '^[A-Z]{3}$');

ALTER TABLE ledger_entries
  ADD CONSTRAINT chk_ledger_currency
  CHECK (currency ~ '^[A-Z]{3}$');