#!/usr/bin/env bash
set -euo pipefail

# Root (tests/tooling if needed)
# uv export --format requirements-txt --no-hashes -o requirements.txt

# Per-service exports (recommended)
uv export --format requirements-txt --no-hashes \
  --project novacard-edge \
  -o novacard-edge/requirements.txt

uv export --format requirements-txt --no-hashes \
  --project novacard-transaction-svc \
  -o novacard-transaction-svc/requirements.txt

uv export --format requirements-txt --no-hashes \
  --project novacard-account-svc \
  -o novacard-account-svc/requirements.txt

uv export --format requirements-txt --no-hashes \
  --project novacard-user-mock \
  -o novacard-user-mock/requirements.txt

# If mocks use uv too, add them:
# uv export --format requirements-txt --no-hashes --project novacard-auth-mock -o novacard-auth-mock/requirements.txt
# uv export --format requirements-txt --no-hashes --project novacard-user-mock -o novacard-user-mock/requirements.txt

echo "✅ requirements.txt exported from uv.lock"