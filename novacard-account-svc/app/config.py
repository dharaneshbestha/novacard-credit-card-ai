from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="account.env", extra="ignore")

    ACCOUNT_BASE_URL: str = "http://account-svc:8004"
    SERVICE_NAME: str = "novacard-account"
    DATABASE_URL: str = "postgresql://novacard:novacard@postgres:5432/novacard"  # local default
    PORT: int = 8004

settings = Settings()