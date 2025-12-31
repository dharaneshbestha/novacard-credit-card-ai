import json
import os
import time

import jwt

KID = os.getenv("EDGE_SVC_ACTIVE_KID", "k2")
KEYS = json.loads(os.getenv("EDGE_SVC_KEYS_JSON", '{"k1":"dev_svc_secret_k1","k2":"dev_svc_secret_k2"}'))
ISS = os.getenv("EDGE_SVC_ISSUER", "novacard-edge")
AUD = os.getenv("TXN_SVC_AUDIENCE", "novacard-transaction")

now = int(time.time())
payload = {
    "sub": "novacard-edge",
    "iss": ISS,
    "aud": AUD,
    "iat": now,
    "exp": now + 120,
    "scope": "service",
}
token = jwt.encode(payload, KEYS[KID], algorithm="HS256", headers={"kid": KID, "typ": "JWT"})
print(token)
