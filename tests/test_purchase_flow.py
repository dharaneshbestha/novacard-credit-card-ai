
import os
import uuid

import httpx
import pytest

pytestmark = pytest.mark.integration


TXN_BASE = os.getenv("TXN_BASE", "http://127.0.0.1:8005")

@pytest.mark.asyncio
async def test_purchase_posted_idempotent(user_jwt):
    idem = f"pytest-{uuid.uuid4()}"
    token = user_jwt
    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": idem,
        "Content-Type": "application/json",
    }

    payload = {"amount_minor": 111, "currency": "USD"}

    async with httpx.AsyncClient(timeout=5.0) as client:
        r1 = await client.post(f"{TXN_BASE}/purchase", headers=headers, json=payload)
        assert r1.status_code in (200, 402, 409, 500)

        body1 = r1.json()
        assert "status" in body1
        assert "transaction_id" in body1

        # re-try same idempotency key → must return same transaction_id + same status/reason
        r2 = await client.post(f"{TXN_BASE}/purchase", headers=headers, json=payload)
        body2 = r2.json()

        assert body2["transaction_id"] == body1["transaction_id"]
        assert body2["status"] == body1["status"]
        assert body2.get("reason") == body1.get("reason")