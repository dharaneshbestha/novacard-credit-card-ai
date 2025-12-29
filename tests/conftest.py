from __future__ import annotations

import json
import os
import time

import pytest
from jose import jwt


@pytest.fixture(scope="session")
def user_jwt() -> str:
    """
    Mints a user JWT that matches the service config.
    Defaults match your dev setup. Override via env vars if needed.
    """
    issuer = os.getenv("USER_JWT_ISSUER", "novacard-auth")
    audience = os.getenv("USER_JWT_AUDIENCE", "novacard-api")
    kid = os.getenv("USER_JWT_ACTIVE_KID", "k1")
    user_id = os.getenv("USER_ID", "user_123")

    keys_json = os.getenv("USER_JWT_KEYS_JSON", '{"k1":"dev_user_jwt_secret_k1"}')
    keys = json.loads(keys_json)
    secret = keys[kid]

    now = int(time.time())
    claims = {
        "sub": user_id,
        "iss": issuer,
        "aud": audience,
        "iat": now,
        "exp": now + 60 * 30,
        "scope": "user",
    }
    return jwt.encode(claims, secret, algorithm="HS256", headers={"kid": kid, "typ": "JWT"})