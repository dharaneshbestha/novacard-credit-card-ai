from __future__ import annotations
from typing import Any

SENSITIVE_KEYS = {"ssn", "itin", "dob", "date_of_birth", "address", "password", "token", "refresh_token"}

def redact_obj(obj: Any) -> Any:
    """
    Shallow+recursive redaction helper for logging only.
    """
    if obj is None:
        return None
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if str(k).lower() in SENSITIVE_KEYS:
                out[k] = "***REDACTED***"
            else:
                out[k] = redact_obj(v)
        return out
    if isinstance(obj, list):
        return [redact_obj(x) for x in obj]
    return obj