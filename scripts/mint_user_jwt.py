from __future__ import annotations

import json
import os
import time

from jose import jwt


def main():
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
        "exp": now + 60 * 30,  # 30 min
        "scope": "user",
    }

    token = jwt.encode(
        claims,
        secret,
        algorithm="HS256",
        headers={"kid": kid, "typ": "JWT"},
    )

    print(token)


if __name__ == "__main__":
    main()
