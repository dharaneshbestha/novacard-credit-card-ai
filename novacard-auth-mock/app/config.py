from __future__ import annotations

import json

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="AUTH_", extra="ignore")

    ISSUER: str = "novacard-auth"
    AUDIENCE: str = "novacard-api"

    ACTIVE_KID: str = "k1"
    KEYS_JSON: str = '{"k1":"dev_user_jwt_secret_k1"}'
    KEYS: dict[str, str] = Field(default_factory=dict)

    # Use 15 minutes for dev realism (not 1 day)
    TOKEN_TTL_SECONDS: int = 900

    @field_validator("KEYS", mode="before")
    @classmethod
    def _parse_keys(cls, v, info):
        raw = info.data.get("KEYS_JSON", "{}")
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("KEYS_JSON must be a JSON object")
        return parsed


settings = Settings()
