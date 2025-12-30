BEGIN;

-- Drop the existing FK (name may differ; adjust if needed)
ALTER TABLE ledger_entries
DROP CONSTRAINT IF EXISTS ledger_entries_transaction_id_fkey;

-- Re-add as DEFERRABLE
ALTER TABLE ledger_entries
ADD CONSTRAINT ledger_entries_transaction_id_fkey
FOREIGN KEY (transaction_id)
REFERENCES transactions(transaction_id)
DEFERRABLE INITIALLY DEFERRED;

COMMIT;