#!/usr/bin/env bash
set -euo pipefail

echo "== NovaCard: DEV GREEN =="

# 0) Ensure docker is running
docker info >/dev/null 2>&1 || { echo "Docker not running"; exit 1; }

# 1) Clean start (keep pgdata volume if you want persistence)
docker compose up -d postgres redis

# 2) Run migrations + seed
docker compose run --rm migrate

# 3) Start services
docker compose up -d auth-mock user-mock account-svc transaction-svc edge

# 4) Wait for health
python - <<'PY'
import time, sys, urllib.request

urls = [
  "http://127.0.0.1:8000/health",
  "http://127.0.0.1:8004/health",
  "http://127.0.0.1:8005/health",
]
deadline = time.time() + 60
last = None
while time.time() < deadline:
  ok = True
  for u in urls:
    try:
      r = urllib.request.urlopen(u, timeout=2)
      if r.status != 200: ok = False
    except Exception as e:
      ok = False
      last = (u, repr(e))
  if ok:
    print("OK: all health endpoints")
    sys.exit(0)
  time.sleep(2)
print("FAILED health:", last)
sys.exit(1)
PY

# 5) Mint USER_JWT for user_123 and run tests
export USER_JWT="$(python scripts/mint_user_jwt.py)"
pytest -q
