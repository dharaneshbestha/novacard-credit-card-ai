from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional


def audit_log(
    *,
    service: str,
    event: str,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    path: Optional[str] = None,
    method: Optional[str] = None,
    status_code: Optional[int] = None,
    detail: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    payload: Dict[str, Any] = {
        "ts": int(time.time()),
        "service": service,
        "event": event,
    }
    if request_id: payload["request_id"] = request_id
    if user_id: payload["user_id"] = user_id
    if path: payload["path"] = path
    if method: payload["method"] = method
    if status_code is not None: payload["status_code"] = status_code
    if detail: payload["detail"] = detail
    if extra: payload.update(extra)

    print(json.dumps(payload, separators=(",", ":"), sort_keys=False))