import os

import httpx
import pytest

pytestmark = pytest.mark.integration

EDGE_BASE = os.getenv("EDGE_BASE", "http://127.0.0.1:8000")
TXN_BASE = os.getenv("TXN_BASE", "http://127.0.0.1:8005")
ACCT_BASE = os.getenv("ACCT_BASE", "http://127.0.0.1:8004")


@pytest.mark.asyncio
async def test_health_endpoints():
    async with httpx.AsyncClient(timeout=2.0) as client:
        for base in (EDGE_BASE, TXN_BASE, ACCT_BASE):
            r = await client.get(f"{base}/health")
            assert r.status_code == 200
