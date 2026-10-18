"""Build the provider chosen in the settings."""

from auditagent.config import Settings, get_settings
from auditagent.llm.base import LLMError, LLMProvider
from auditagent.llm.gemini import GeminiProvider


def build_provider(settings: Settings | None = None) -> LLMProvider:
    s = settings or get_settings()
    if s.llm_provider == "gemini":
        if s.gemini_api_key is None:
            raise LLMError("GEMINI_API_KEY is not set. Put it in your .env file.")
        return GeminiProvider(s.gemini_api_key.get_secret_value(), s.gemini_model)
    raise LLMError(f"Unknown LLM_PROVIDER: {s.llm_provider}")