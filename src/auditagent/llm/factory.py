"""Build the provider chosen in the settings."""

from auditagent.config import Settings, get_settings
from auditagent.llm.base import LLMError, LLMProvider
from auditagent.llm.gemini import GeminiProvider
from auditagent.llm.ollama import OllamaProvider


def build_provider(settings: Settings | None = None) -> LLMProvider:
    """The LLM provider named in LLM_PROVIDER ("gemini" or "ollama")."""
    s = settings or get_settings()
    if s.llm_provider == "gemini":
        if s.gemini_api_key is None:
            raise LLMError("GEMINI_API_KEY is not set. Put it in your .env file.")
        return GeminiProvider(s.gemini_api_key.get_secret_value(), s.gemini_model)
    if s.llm_provider == "ollama":
        return OllamaProvider(
            s.ollama_model,
            base_url=s.ollama_base_url,
            num_ctx=s.ollama_num_ctx,
            timeout=s.ollama_timeout,
        )
    raise LLMError(f"Unknown LLM_PROVIDER: {s.llm_provider}")
