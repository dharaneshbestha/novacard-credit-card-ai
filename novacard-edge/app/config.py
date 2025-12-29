from __future__ import annotations

import json

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # print("[EDGE CONFIG] EDGE_DEV_REUSE_SVC_TOKEN:", settings.EDGE_DEV_REUSE_SVC_TOKEN)
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="EDGE_",
        extra="ignore",
    )

    # Downstream services
    AUTH_BASE_URL: AnyHttpUrl = "http://127.0.0.1:8001"
    USER_BASE_URL: AnyHttpUrl = "http://127.0.0.1:8002"
    KYC_BASE_URL: AnyHttpUrl = "http://127.0.0.1:8003"
    TXN_BASE_URL: AnyHttpUrl = "http://transaction-svc:8005"
    # ---- User JWT verification (Route A: HS256 secrets) ----
    USER_JWT_ISSUER: str = "novacard-auth"
    USER_JWT_AUDIENCE: str = "novacard-api"
    USER_JWT_ACTIVE_KID: str = "k1"
    USER_JWT_KEYS_JSON: str = '{"k1":"dev_user_jwt_secret_k1"}'
    USER_JWT_KEYS: dict[str, str] = Field(default_factory=dict)

    # (Future) JWKS - not used in Route A middleware
    JWKS_URL: str = "http://127.0.0.1:8001/.well-known/jwks.json"
    JWKS_CACHE_SECONDS: int = 900

    # Rate limiting
    RL_AUTH_PER_IP_PER_MIN: int = 10
    RL_PUBLIC_PER_IP_PER_MIN: int = 60
    RL_AUTHD_PER_USER_PER_MIN: int = 120

    # Idempotency
    IDEM_TTL_SECONDS: int = 3600

    # ---- Service-to-service auth (Edge -> downstream) ----
    SVC_ISSUER: str = "novacard-edge"
    SVC_ACTIVE_KID: str = "k1"
    SVC_KEYS_JSON: str = '{"k1":"dev_svc_secret_k1","k2":"dev_svc_secret_k2"}'
    SVC_KEYS: dict[str, str] = Field(default_factory=dict)
    SVC_TOKEN_TTL_SECONDS: int = 60

    # Redis
    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    # Dev-only toggles
    DEV_REUSE_SVC_TOKEN: bool = False

    # Service identity
    SERVICE_NAME: str = "novacard-edge"

    # Request signing (Edge -> downstream)
    SIGNING_ENABLED: bool = True
    SIGNING_SECRET: str = "dev_signing_secret_change_me"
    SIGNING_KEY_ID: str = "sig-k1"
    SIGNING_TOLERANCE_SECONDS: int = 60

    # ---------------- Validators ----------------
    @field_validator("USER_JWT_KEYS", mode="before")
    @classmethod
    def parse_user_jwt_keys(cls, v, info):
        raw = info.data.get("USER_JWT_KEYS_JSON", "{}")
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("USER_JWT_KEYS_JSON must be a JSON object")
        return parsed

    @field_validator("SVC_KEYS", mode="before")
    @classmethod
    def parse_svc_keys(cls, v, info):
        raw = info.data.get("SVC_KEYS_JSON", "{}")
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("SVC_KEYS_JSON must be a JSON object")
        return parsed


settings = Settings()

# TEMP DEBUG (remove after you see correct output once)
print("[EDGE CONFIG] USER_JWT_KEYS:", settings.USER_JWT_KEYS)
print("[EDGE CONFIG] USER_JWT_ISSUER:", settings.USER_JWT_ISSUER)
print("[EDGE CONFIG] USER_JWT_AUDIENCE:", settings.USER_JWT_AUDIENCE)