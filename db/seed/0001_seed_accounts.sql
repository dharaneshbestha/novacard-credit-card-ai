-- db/migrations_clean/0900_seed.sql

-- Create USER account


INSERT INTO accounts (account_id, user_id, account_type, currency, status, credit_limit_minor)
VALUES
  ('cfa78f0e-37af-4fa7-8793-950d08012fdc'::uuid, 'user_123', 'USER', 'USD', 'ACTIVE', 100000);

-- merchant_system (fixed forever)
INSERT INTO accounts (account_id, user_id, account_type, currency, status, credit_limit_minor)
VALUES
  ('35a3b574-44d2-4c19-9bd1-a76508ca346f'::uuid, 'merchant_system', 'MERCHANT', 'USD', 'ACTIVE', 0);

-- INSERT INTO accounts (user_id, account_type, currency, status, credit_limit_minor)
-- VALUES ('user_123', 'USER', 'USD', 'ACTIVE', 100000)
-- ON CONFLICT DO NOTHING;

-- -- Create MERCHANT/SYSTEM account
-- INSERT INTO accounts (user_id, account_type, currency, status, credit_limit_minor)
-- VALUES ('merchant_system', 'MERCHANT', 'USD', 'ACTIVE', 0)
-- ON CONFLICT DO NOTHING;

-- Create snapshots for all accounts (optional but recommended)
-- INSERT INTO account_balance_snapshots (account_id, balance_minor)
-- SELECT a.account_id, 0
-- FROM accounts a
-- ON CONFLICT (account_id) DO NOTHING;