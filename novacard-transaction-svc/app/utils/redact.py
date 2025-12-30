from __future__ import annotations
from typing import Any

SENSITIVE_KEYS = {"authorization", "password", "token", "secret", "api_key"}

def redact_dict(d: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in d.items():
        lk = str(k).lower()
        if lk in SENSITIVE_KEYS or "token" in lk or "secret" in lk:
            out[k] = "***REDACTED***"
        else:
            out[k] = v
    return out