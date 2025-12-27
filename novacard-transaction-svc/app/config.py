from __future__ import annotations

import json
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="TXN_", extra="ignore")

    SERVICE_NAME: str = "transaction"

    # Postgres
    DATABASE_URL: str = "postgresql://novacard:novacard@postgres:5432/novacard"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    IDEM_TTL_SECONDS: int = 3600

    # Merchant/system account used for CREDIT leg
    MERCHANT_ACCOUNT_ID: str = "3bdb55cd-a934-4c92-890d-d3e2e1a14fdc"

    # User JWT validation (dev HS256 path)
    USER_JWT_ISSUER: str = "novacard-auth"
    USER_JWT_AUDIENCE: str = "novacard-api"
    USER_JWT_KEYS_JSON: str = '{"k1":"dev_user_jwt_secret_k1"}'
    USER_JWT_KEYS: dict[str, str] = Field(default_factory=dict)
    USER_JWT_ACTIVE_KID: str = "k1"

    @field_validator("USER_JWT_KEYS", mode="before")
    @classmethod
    def _parse_user_keys(cls, v, info):
        raw = info.data.get("USER_JWT_KEYS_JSON", "{}")
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("USER_JWT_KEYS_JSON must be an object")
        return parsed


settings = Settings()