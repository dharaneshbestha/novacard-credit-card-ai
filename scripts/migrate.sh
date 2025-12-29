#!/usr/bin/env bash
set -euo pipefail

DB_URL="${DATABASE_URL:-}"
if [[ -z "$DB_URL" ]]; then
  echo "DATABASE_URL is not set"
  exit 1
fi

echo "Running migrations against: $DB_URL"

# Ensure migration table exists
psql "$DB_URL" -v ON_ERROR_STOP=1 -f db/migrations/0000_schema_migrations.sql

apply_one () {
  local file="$1"
  local base
  base="$(basename "$file")"
  local checksum
  checksum="$(shasum -a 256 "$file" | awk '{print $1}')"

  local exists
  exists="$(psql "$DB_URL" -tAc "SELECT 1 FROM schema_migrations WHERE version='$base' LIMIT 1;")"
  if [[ "$exists" == "1" ]]; then
    # Optional checksum enforcement:
    local old
    old="$(psql "$DB_URL" -tAc "SELECT checksum FROM schema_migrations WHERE version='$base';" | xargs)"
    if [[ "$old" != "$checksum" ]]; then
      echo "ERROR: checksum mismatch for $base"
      echo "  db=$old"
      echo "  fs=$checksum"
      exit 1
    fi
    echo "SKIP $base"
    return
  fi

  echo "APPLY $base"
  psql "$DB_URL" -v ON_ERROR_STOP=1 -f "$file"

  psql "$DB_URL" -v ON_ERROR_STOP=1 -c \
    "INSERT INTO schema_migrations(version, checksum) VALUES ('$base', '$checksum');"

  echo "DONE  $base"
}

# Apply all migrations except 0000 first file (it can be rerun safely anyway)
for f in $(ls -1 db/migrations/*.sql | sort); do
  apply_one "$f"
done

echo "All migrations applied."