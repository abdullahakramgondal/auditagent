"""Settings read from environment variables and the local .env file."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All settings of the app. Environment variables and .env override these defaults."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_provider: str = "gemini"  # "gemini" or "ollama"
    gemini_api_key: SecretStr | None = None  # SecretStr hides the value in logs and repr
    gemini_model: str = "gemini-3.1-flash-lite"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_num_ctx: int = 8192  # context window in tokens; Ollama's default is too small for 8 to 11 clauses
    ollama_timeout: float = 600.0  # seconds to wait for one answer; a small model on a CPU is slow
    database_url: str = "sqlite:///./auditagent.db"


@lru_cache
def get_settings() -> Settings:
    """The settings, read once per process."""
    return Settings()