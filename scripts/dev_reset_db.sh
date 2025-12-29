#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./scripts/dev_reset_db.sh
#   ./scripts/dev_reset_db.sh --nuke-volumes   # WARNING: deletes pg volume(s)

COMPOSE="${COMPOSE:-docker compose}"
POSTGRES_SVC="${POSTGRES_SVC:-postgres}"

DB_USER="${DB_USER:-novacard}"
DB_NAME="${DB_NAME:-novacard}"

MIG_DIR="${MIG_DIR:-db/migrations}"

NUKE_VOLUMES="false"
if [[ "${1:-}" == "--nuke-volumes" ]]; then
  NUKE_VOLUMES="true"
fi

log() { printf "\n\033[1;34m==>\033[0m %s\n" "$*"; }
die() { printf "\n\033[1;31mERROR:\033[0m %s\n" "$*"; exit 1; }

psql_in_pg() {
  # Run psql inside postgres container
  $COMPOSE exec -T "$POSTGRES_SVC" sh -lc "psql -U '$DB_USER' -d '$DB_NAME' -v ON_ERROR_STOP=1 $*"
}

apply_sql_file() {
  local f="$1"
  [[ -f "$f" ]] || die "Missing migration file: $f"
  log "APPLY $f"
  psql_in_pg "-f /work/$f"
}

wait_for_pg() {
  log "Waiting for Postgres..."
  local tries=60
  for _ in $(seq 1 "$tries"); do
    if $COMPOSE exec -T "$POSTGRES_SVC" sh -lc "pg_isready -U '$DB_USER' -d '$DB_NAME' >/dev/null 2>&1"; then
      log "Postgres is ready."
      return 0
    fi
    sleep 1
  done
  die "Postgres did not become ready."
}

log "Stopping stack..."
if [[ "$NUKE_VOLUMES" == "true" ]]; then
  log "NUKE MODE: docker compose down -v"
  $COMPOSE down -v
else
  $COMPOSE down
fi

log "Starting Postgres + Redis..."
$COMPOSE up -d "$POSTGRES_SVC" redis
wait_for_pg

log "Resetting DB schema: DROP + CREATE public..."
psql_in_pg "-c \"DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;\""

# ---------------------------
# 1) Base schema migrations
# ---------------------------
# This is your REAL schema (creates accounts/transactions/ledger_entries)
apply_sql_file "$MIG_DIR/c7_1_a_schema.sql"

# Optional schema_migrations table (keeps it around if you use it)
apply_sql_file "$MIG_DIR/0000_schema_migrations.sql"

# ---------------------------
# 2) Constraints / hardening / indexes
# ---------------------------
apply_sql_file "$MIG_DIR/c7_1_a_2_constraints.sql"
apply_sql_file "$MIG_DIR/c7_1_a_345_hardening.sql"
apply_sql_file "$MIG_DIR/c7_1_a_6_indexes.sql"

# Deferrable FK (important for insert order flexibility)
apply_sql_file "$MIG_DIR/2025-12-29_01_deferrable_ledger_fk.sql"

# ---------------------------
# 3) Snapshot schema + helper + rebuild function
# ---------------------------
apply_sql_file "$MIG_DIR/2025-12-25_01_create_account_balance_snapshots.sql"
apply_sql_file "$MIG_DIR/2025-12-25_03_snapshot_upsert_helper.sql"

# This migration uses psql variables like :'account_id'.
# We apply it with a dummy UUID to satisfy parsing/creation.
log "APPLY $MIG_DIR/2025-12-25_04_rebuild_snapshot_from_ledger.sql (with -v account_id=...)"
psql_in_pg "-v account_id='00000000-0000-0000-0000-000000000000' -f /work/$MIG_DIR/2025-12-25_04_rebuild_snapshot_from_ledger.sql"

# ---------------------------
# 4) Seed: user + merchant accounts
# ---------------------------
log "Seeding accounts (user_123 USER + merchant_system MERCHANT) + snapshots..."

psql_in_pg "-c \"
DELETE FROM ledger_entries;
DELETE FROM transactions;
DELETE FROM account_balance_snapshots;
DELETE FROM accounts WHERE user_id IN ('user_123','merchant_system');

INSERT INTO accounts (account_id, user_id, account_type, currency, status, credit_limit_minor)
VALUES
  (gen_random_uuid(), 'user_123', 'USER', 'USD', 'ACTIVE', 100000),
  (gen_random_uuid(), 'merchant_system', 'MERCHANT', 'USD', 'ACTIVE', NULL);

INSERT INTO account_balance_snapshots (account_id, balance_minor, updated_at)
SELECT account_id, 0, now()
FROM accounts;

SELECT account_id::text, user_id, account_type, status, currency, credit_limit_minor
FROM accounts
ORDER BY user_id;
\""

# Backfill snapshots script (safe even if already inserted, depending on your SQL)
apply_sql_file "$MIG_DIR/2025-12-25_02_backfill_account_balance_snapshots.sql"

log "Counts:"
psql_in_pg "-c \"select count(*) as accounts from accounts; select count(*) as snapshots from account_balance_snapshots;\""

log "Tables:"
psql_in_pg "-c \"\\dt\""

log "Starting full stack..."
$COMPOSE up -d

log "Done. Sanity checks:"
echo "  curl -s http://127.0.0.1:8000/health"
echo "  curl -s http://127.0.0.1:8005/health"
echo "  docker compose exec -T postgres sh -lc \"psql -U novacard -d novacard -c 'select user_id,account_type,status from accounts order by user_id;'\""