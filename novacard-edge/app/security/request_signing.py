from __future__ import annotations

import base64
import hashlib
import hmac
import time


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

def body_sha256_hex(body: bytes) -> str:
    return hashlib.sha256(body or b"").hexdigest()

def canonical_string(method: str, path: str, query: str, ts: int, body_hash: str) -> str:
    # Keep this canonical string IDENTICAL in verifier
    return "\n".join([
        method.upper(),
        path,
        query or "",
        str(ts),
        body_hash,
    ])

def sign_request(method: str, path: str, query: str, body: bytes, secret: str, key_id: str) -> dict[str, str]:
    ts = int(time.time())
    bh = body_sha256_hex(body)
    canon = canonical_string(method, path, query, ts, bh).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), canon, hashlib.sha256).digest()
    return {
        "X-Signature-KeyId": key_id,
        "X-Signature-Timestamp": str(ts),
        "X-Content-SHA256": bh,
        "X-Signature": _b64url(sig),
    }