from __future__ import annotations

from fastapi import HTTPException, Request
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError

from app.config import settings


async def require_user(request: Request) -> dict:
    """
    Dev path: validate HS256 token using USER_JWT_KEYS (local keyring).
    Expects Authorization: Bearer <jwt>
    """
    hdr = request.headers.get("authorization", "")
    if not hdr.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail={"error": "missing_token"})

    token = hdr.split(" ", 1)[1].strip()

    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid") or settings.USER_JWT_ACTIVE_KID
        secret = settings.USER_JWT_KEYS.get(kid)
        if not secret:
            raise HTTPException(status_code=401, detail={"error": "invalid_token", "detail": f"unknown_kid={kid}"})

        claims = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            issuer=settings.USER_JWT_ISSUER,
            audience=settings.USER_JWT_AUDIENCE,
            options={"verify_exp": True},
        )
        request.state.user_id = claims.get("sub")
        return claims

    except ExpiredSignatureError as e:
        raise HTTPException(status_code=401, detail={"error": "token_expired"}) from e
    except JWTError as e:
        raise HTTPException(status_code=401, detail={"error": "invalid_token", "detail": str(e)}) from e