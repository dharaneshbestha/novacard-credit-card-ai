-- C7.2.5 - Rebuild a single account snapshot from authoritative ledger
-- Usage:
--   \set account_id '...uuid...'
--   then run this file

BEGIN;

-- Ensure snapshot row exists
INSERT INTO account_balance_snapshots (account_id, balance_minor)
VALUES (:'account_id'::uuid, 0)
ON CONFLICT (account_id) DO NOTHING;

-- Recompute balance from ledger entries (authoritative)
UPDATE account_balance_snapshots s
SET balance_minor = COALESCE(x.balance_minor, 0),
    updated_at = now()
FROM (
  SELECT
    account_id,
    SUM(
      CASE
        WHEN entry_type='DEBIT'  THEN -amount_minor
        WHEN entry_type='CREDIT' THEN  amount_minor
        ELSE 0
      END
    ) AS balance_minor
  FROM ledger_entries
  WHERE account_id = :'account_id'::uuid
  GROUP BY account_id
) x
WHERE s.account_id = x.account_id;

COMMIT;

-- docker compose exec -T postgres psql -U novacard -d novacard -v account_id='df321457-7f87-488f-ab14-9b2f6411acde' \
--  -f /dev/stdin < sql/migrations/2025-12-25_04_rebuild_snapshot_from_ledger.sql