#!/usr/bin/env bash
set -euo pipefail

echo "==> Reset DB"
./scripts/dev_reset_db.sh

echo "==> Build + start services"
docker compose up -d --build

echo "==> Wait for health"
for url in \
  "http://127.0.0.1:8000/health" \
  "http://127.0.0.1:8005/health" \
  "http://127.0.0.1:8004/health"
do
  echo "Checking $url"
  for i in {1..40}; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "OK $url"
      break
    fi
    sleep 1
    if [ "$i" -eq 40 ]; then
      echo "FAILED health: $url"
      exit 1
    fi
  done
done

echo "==> Mint token"
TOKEN="$(python scripts/mint_user_jwt.py)"
export USER_JWT="$TOKEN"
export EDGE_BASE="http://127.0.0.1:8000"

echo "==> Smoke purchase"
curl -sS -i "http://127.0.0.1:8000/transactions/purchase" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: docker-green-1" \
  -H "Content-Type: application/json" \
  -d '{"amount_minor":111,"currency":"USD"}' | head -n 40

echo "==> Run integration tests"
pytest -m integration -q

echo "==> Done: GREEN"