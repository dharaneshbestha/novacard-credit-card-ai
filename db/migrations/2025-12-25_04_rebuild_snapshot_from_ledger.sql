BEGIN;

-- Rebuild snapshots from authoritative ledger entries.
-- Safe for migrations: no psql variables, no runtime params required.

CREATE OR REPLACE FUNCTION rebuild_account_balance_snapshots(p_account_id uuid DEFAULT NULL)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
  -- Ensure snapshot rows exist for any account we might rebuild
  INSERT INTO account_balance_snapshots (account_id, balance_minor, as_of_ledger_entry_id, updated_at)
  SELECT a.account_id, 0, NULL, now()
  FROM accounts a
  WHERE p_account_id IS NULL OR a.account_id = p_account_id
  ON CONFLICT (account_id) DO NOTHING;

  -- Recompute balances from ledger (authoritative)
  UPDATE account_balance_snapshots s
  SET balance_minor = COALESCE(x.balance_minor, 0),
      as_of_ledger_entry_id = x.max_ledger_entry_id,
      updated_at = now()
  FROM (
    SELECT
      le.account_id,
      SUM(
        CASE
          WHEN le.entry_type = 'DEBIT'  THEN -le.amount_minor
          WHEN le.entry_type = 'CREDIT' THEN  le.amount_minor
          ELSE 0
        END
      ) AS balance_minor,
      MAX(le.ledger_entry_id) AS max_ledger_entry_id
    FROM ledger_entries le
    WHERE p_account_id IS NULL OR le.account_id = p_account_id
    GROUP BY le.account_id
  ) x
  WHERE s.account_id = x.account_id;

  -- If an account has zero ledger rows, balance stays whatever it was.
  -- (If you prefer forcing missing-ledger accounts to 0, tell me and I’ll adjust.)
END;
$$;

COMMIT;