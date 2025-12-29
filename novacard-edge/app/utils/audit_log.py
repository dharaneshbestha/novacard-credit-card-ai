from __future__ import annotations

import json
import time
from typing import Any


def audit_log(
    *,
    service: str,
    event: str,
    request_id: str | None = None,
    user_id: str | None = None,
    path: str | None = None,
    method: str | None = None,
    status_code: int | None = None,
    detail: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
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