"""Gemini provider (Google AI Studio API key)."""

from google import genai
from google.genai import errors, types
from pydantic import BaseModel
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from auditagent.llm.base import LLMError, LLMTransientError

TRANSIENT_CODES = {429, 500, 502, 503, 504}


class GeminiProvider:
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str,
        client=None,
        retry_wait: float = 2.0,
        max_retries: int = 5,
    ):
        self.model = model
        self._client = client or genai.Client(api_key=api_key)
        self._retry_wait = retry_wait
        self._max_retries = max_retries

    def generate_json(self, system: str, prompt: str, schema: type[BaseModel]) -> str:
        retrying = Retrying(
            retry=retry_if_exception_type(LLMTransientError),
            wait=wait_exponential(multiplier=self._retry_wait, max=60),
            stop=stop_after_attempt(self._max_retries),
            reraise=True,
        )
        return retrying(self._call_once, system, prompt, schema)

    def _call_once(self, system: str, prompt: str, schema: type[BaseModel]) -> str:
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=schema,
        )
        try:
            response = self._client.models.generate_content(
                model=self.model, contents=prompt, config=config
            )
        except errors.APIError as exc:
            detail = getattr(exc, "status", "") or "no status"
            if exc.code in TRANSIENT_CODES:
                raise LLMTransientError(f"Gemini {exc.code} ({detail}), temporary") from exc
            raise LLMError(f"Gemini API error {exc.code} ({detail})") from exc
        return response.text or ""  # empty text fails validation and triggers a retry upstream

    def list_models(self) -> list[str]:
        """Models this key may call for text generation (names without the 'models/' prefix)."""
        names = []
        for m in self._client.models.list():
            if "generateContent" in (m.supported_actions or []):
                names.append((m.name or "").removeprefix("models/"))
        return sorted(names)
