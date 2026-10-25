import pytest

from auditagent.config import Settings
from auditagent.llm.base import LLMError
from auditagent.llm.factory import build_provider


def test_api_key_is_hidden_in_repr_but_available_to_code():
    s = Settings(_env_file=None, gemini_api_key="super-secret-key-123")
    assert "super-secret-key-123" not in repr(s)
    assert s.gemini_api_key.get_secret_value() == "super-secret-key-123"


def test_missing_key_gives_a_clear_error():
    s = Settings(_env_file=None, gemini_api_key=None)
    with pytest.raises(LLMError, match="GEMINI_API_KEY"):
        build_provider(s)


def test_unknown_provider_is_rejected():
    s = Settings(_env_file=None, llm_provider="nonsense", gemini_api_key="k")
    with pytest.raises(LLMError, match="Unknown LLM_PROVIDER"):
        build_provider(s)


def test_gemini_provider_is_built_from_settings():
    s = Settings(_env_file=None, gemini_api_key="k", gemini_model="gemini-test")
    provider = build_provider(s)
    assert provider.name == "gemini" and provider.model == "gemini-test"


def test_ollama_provider_is_built_from_settings_and_needs_no_key():
    s = Settings(_env_file=None, llm_provider="ollama", gemini_api_key=None, ollama_model="tiny:1b")
    provider = build_provider(s)
    assert provider.name == "ollama" and provider.model == "tiny:1b"