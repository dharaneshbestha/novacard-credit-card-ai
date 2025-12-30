#!/usr/bin/env bash
set -euo pipefail

DB_URL="${DATABASE_URL:-}"
if [[ -z "$DB_URL" ]]; then
  echo "ERROR: DATABASE_URL is not set"
  exit 1
fi

echo "Running migrations against: ${DB_URL/novacard:novacard/novacard:***}"

MIG_DIR="/db/migrations"
SEED_DIR="/db/seed"

if [[ ! -d "$MIG_DIR" ]]; then
  echo "ERROR: migrations directory not found: $MIG_DIR"
  exit 1
fi

shopt -s nullglob
migs=("$MIG_DIR"/*.sql)
shopt -u nullglob

if [[ ${#migs[@]} -eq 0 ]]; then
  echo "ERROR: no migration files found in $MIG_DIR"
  exit 1
fi

for f in "${migs[@]}"; do
  echo "APPLY MIGRATION $(basename "$f")"
  psql "$DB_URL" -v ON_ERROR_STOP=1 -f "$f"
done

if [[ -d "$SEED_DIR" ]]; then
  shopt -s nullglob
  seeds=("$SEED_DIR"/*.sql)
  shopt -u nullglob
  for f in "${seeds[@]}"; do
    echo "APPLY SEED $(basename "$f")"
    psql "$DB_URL" -v ON_ERROR_STOP=1 -f "$f"
  done
fi

echo "Migrations + seed complete."