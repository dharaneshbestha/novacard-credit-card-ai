from __future__ import annotations

import json
from typing import Any

from app.config import settings
from app.redis_client import get_redis
from app.metrics import idempotency_total


class IdemInProgress(Exception):
    pass


def _lock_key(user_id: str, idem_key: str) -> str:
    return f"txn:lock:{user_id}:{idem_key}"


def _final_key(user_id: str, idem_key: str) -> str:
    return f"txn:final:{user_id}:{idem_key}"


async def idem_get_final(user_id: str, idem_key: str) -> dict[str, Any] | None:
    r = await get_redis()
    raw = await r.get(_final_key(user_id, idem_key))
    if raw is None:
        return None

    # aioredis can return str (decode_responses=True) or bytes
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="ignore")

    raw = raw.strip()
    if not raw:
        # self-heal: empty value should never happen
        await r.delete(_final_key(user_id, idem_key))
        idempotency_total.labels(result="final_corrupt_empty").inc()
        return None

    try:
        obj = json.loads(raw)
        idempotency_total.labels(result="final_cache_hit").inc()
        return obj
    except Exception:
        # self-heal: corrupt JSON should not poison the system
        await r.delete(_final_key(user_id, idem_key))
        idempotency_total.labels(result="final_corrupt_json").inc()
        return None


async def idem_try_lock(user_id: str, idem_key: str) -> None:
    r = await get_redis()
    ok = await r.set(
        _lock_key(user_id, idem_key),
        "LOCKED",
        ex=int(settings.IDEM_TTL_SECONDS),
        nx=True,
    )
    if not ok:
        idempotency_total.labels(result="in_progress").inc()
        raise IdemInProgress()
    idempotency_total.labels(result="lock_acquired").inc()

def _lock_key(user_id: str, idem_key: str) -> str:
    return f"txn:lock:{user_id}:{idem_key}"

def _final_key(user_id: str, idem_key: str) -> str:
    return f"txn:final:{user_id}:{idem_key}"

async def idem_set_final(user_id: str, idem_key: str, response: dict) -> None:
    r = await get_redis()
    await r.set(_final_key(user_id, idem_key), json.dumps(response), ex=int(settings.IDEM_TTL_SECONDS))
    await r.delete(_lock_key(user_id, idem_key))  # ✅ critical

# async def idem_set_final(user_id: str, idem_key: str, response: dict[str, Any]) -> None:
#     r = await get_redis()
#     await r.set(_final_key(user_id, idem_key), json.dumps(response), ex=int(settings.IDEM_TTL_SECONDS))
#     await r.delete(_lock_key(user_id, idem_key))  # ✅ release lock
#     idempotency_total.labels(result="final_written").inc()