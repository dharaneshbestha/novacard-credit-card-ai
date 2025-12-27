from __future__ import annotations
from cachetools import TTLCache
import httpx

class JwksClient:
    def __init__(self, jwks_url: str, cache_seconds: int = 900):
        self.jwks_url = jwks_url
        self._cache = TTLCache(maxsize=2, ttl=cache_seconds)

    async def get_jwks(self) -> dict:
        if "jwks" in self._cache:
            return self._cache["jwks"]

        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(self.jwks_url)
            r.raise_for_status()
            jwks = r.json()
            self._cache["jwks"] = jwks
            return jwks