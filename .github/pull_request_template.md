## Summary
- What changed?

## Risk
- [ ] Low
- [ ] Medium
- [ ] High (explain)

## FinTech Safety Checklist
- [ ] Idempotency behavior preserved (lock released + final cached)
- [ ] Ledger writes remain atomic (2-leg entries in same DB tx)
- [ ] No PII leakage in logs (redaction applied where relevant)
- [ ] Request-id propagated (edge → downstream) and logged

## Testing
- [ ] `ruff format --check .`
- [ ] `ruff check .`
- [ ] `pytest -q`
- [ ] Docker green path (migrate → up → health → purchase) verified