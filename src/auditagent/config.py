"""Settings read from environment variables and the local .env file."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_provider: str = "gemini"
    gemini_api_key: SecretStr | None = None  # SecretStr hides the value in logs and repr
    gemini_model: str = "gemini-3.1-flash-lite"
    database_url: str = "sqlite:///./auditagent.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()