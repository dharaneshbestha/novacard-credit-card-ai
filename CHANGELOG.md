# Changelog

All notable changes to this repository will be documented in this file.

This project uses a simple, audit-friendly format:
- **Added**: new features
- **Changed**: modifications to existing behavior
- **Fixed**: bug fixes
- **Security**: auth/signing/replay/idempotency changes
- **DB**: schema/migrations/seed changes
- **Ops/CI**: docker/dev scripts/github actions

---

## [Unreleased]
### Added
- TBD

### Changed
- TBD

### Fixed
- TBD

### Security
- TBD

### DB
- TBD

### Ops/CI
- TBD

---

## [v0.7.4-green] - 2025-12-30
### Added
- End-to-end Docker “green path” across core services (edge, transaction-svc, account-svc, auth-mock, user-mock).
- Integration tests for health + purchase idempotency flow.
- Token minting helper for CI/integration tests (`scripts/mint_user_jwt.py`).

### Changed
- Standardized docker bring-up order to include: postgres → migrate → services → health checks → integration tests.
- Improved idempotency behavior to reliably store final response and release locks after completion.

### Fixed
- Multiple stability fixes to restore consistent purchase flow execution and prevent repeated “in progress” idempotency states.
- Fixed runtime issues around UUID handling and request flows that blocked end-to-end operation.

### Security
- User JWT verification flow stabilized for transaction-svc (consistent issuer/audience/keys wiring).
- Service-to-service auth/signing/replay protections operating in Docker environment.

### DB
- Migrations + seed run via `docker compose run --rm migrate` and verified.
- Core tables present and operational:
  - `accounts`
  - `transactions`
  - `ledger_entries`
  - `account_balance_snapshots`
  - `schema_migrations`

### Ops/CI
- GitHub Actions CI pipeline runs:
  - ruff format + lint
  - docker build + up + migrate + seed
  - health checks + integration tests

---

## [v0.7.3-green] - 2025-12-29
### Added
- Verified “green” Docker baseline for prior stable snapshot.

### Notes
- Use this tag as a rollback point if new work destabilizes the repo.