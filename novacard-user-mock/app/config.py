from __future__ import annotations

import json

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="USER_", extra="ignore")

    # Redis
    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    # Service-to-service verification (Edge -> User)
    SVC_EXPECTED_ISSUER: str = "novacard-edge"
    SVC_AUDIENCE: str = "novacard-user"

    SIGNING_REQUIRED: bool = True
    SIGNING_SECRET: str = "dev_signing_secret_change_me"
    SIGNING_KEY_ID: str = "sig-k1"
    SIGNING_TOLERANCE_SECONDS: int = 60

    SVC_KEYS_JSON: str = '{"k1":"dev_svc_secret_k1","k2":"dev_svc_secret_k2"}'
    SVC_KEYS: dict[str, str] = Field(default_factory=dict)
    REPLAY_FAIL_OPEN: bool = False  # Prod-safe defaults

    @field_validator("SVC_KEYS", mode="before")
    @classmethod
    def parse_svc_keys(cls, v, info):
        raw = info.data.get("SVC_KEYS_JSON", "{}")
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("SVC_KEYS_JSON must be a JSON object")
        return parsed


settings = Settings()

# TEMP DEBUG (remove after first run)
print("[USER CONFIG] SVC_KEYS:", settings.SVC_KEYS)
print("[USER CONFIG] SVC_EXPECTED_ISSUER:", settings.SVC_EXPECTED_ISSUER)
print("[USER CONFIG] SVC_AUDIENCE:", settings.SVC_AUDIENCE)
