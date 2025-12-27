-- Optional helper migration (safe, defensive)
-- Ensures snapshot rows always exist even if created after accounts.
BEGIN;

-- No schema change here; just a documented pattern for app code:
-- INSERT ... ON CONFLICT DO NOTHING
-- We'll implement it in code.

COMMIT;