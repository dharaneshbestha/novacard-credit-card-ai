#!/usr/bin/env bash
set -euo pipefail

echo "⚠️  Hard reset: deleting postgres volume pgdata (ALL DATA LOST)"
docker compose down -v
docker volume rm -f "$(basename "$PWD")_pgdata" 2>/dev/null || true

echo "Starting postgres..."
docker compose up -d postgres

echo "Waiting for postgres health..."
until docker compose ps --status running | grep -q postgres; do
  sleep 1
done

echo "Running migrate (schema + seed)..."
docker compose run --rm migrate

echo "✅ DB reset complete."