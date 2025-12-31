import os
import uuid

import httpx
import pytest

pytestmark = pytest.mark.integration


# TXN_BASE = os.getenv("TXN_BASE", "http://127.0.0.1:8005")
EDGE_BASE = os.getenv("EDGE_BASE", "http://127.0.0.1:8000")


@pytest.mark.asyncio
async def test_purchase_posted_idempotent():
    idem = f"pytest-{uuid.uuid4()}"
    token = os.getenv("USER_JWT")
    if not token:
        pytest.skip("USER_JWT not set; skipping purchase flow integration test", allow_module_level=True)

    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": idem,
        "Content-Type": "application/json",
    }
    payload = {"amount_minor": 111, "currency": "USD"}

    async with httpx.AsyncClient(timeout=5.0) as client:
        r1 = await client.post(f"{EDGE_BASE}/transactions/purchase", headers=headers, json=payload)

        try:
            body1 = r1.json()
        except Exception:
            pytest.fail(f"Non-JSON response. status={r1.status_code} body={r1.text}")

        print("R1 status:", r1.status_code)
        print("R1 body:", body1)

        assert r1.status_code in (200, 402, 409, 500), f"Unexpected status={r1.status_code} body={body1}"

        # Contract checks (no KeyError)
        assert "status" in body1, f"Missing status. status={r1.status_code} body={body1}"
        assert "transaction_id" in body1, f"Missing transaction_id. status={r1.status_code} body={body1}"
        assert "reason" in body1, f"Missing reason. status={r1.status_code} body={body1}"

        r2 = await client.post(f"{EDGE_BASE}/transactions/purchase", headers=headers, json=payload)
        body2 = r2.json()

        print("R2 status:", r2.status_code)
        print("R2 body:", body2)

        assert body2.get("transaction_id") == body1.get("transaction_id")
        assert body2.get("status") == body1.get("status")
        assert body2.get("reason") == body1.get("reason")
