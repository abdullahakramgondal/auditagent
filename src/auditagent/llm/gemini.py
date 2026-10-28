"""Gemini provider (Google AI Studio API key)."""

import logging

from google import genai
from google.genai import errors, types
from pydantic import BaseModel
from tenacity import (
    RetryCallState,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from auditagent.llm.base import LLMError, LLMTransientError

TRANSIENT_CODES = {429, 500, 502, 503, 504}

logger = logging.getLogger(__name__)


class GeminiProvider:
    """Gemini through the Google AI Studio API. A rate limit or a temporary outage is retried with a growing wait."""

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
        self.retries = 0  # how many times a call had to be tried again
        self.seconds_waited = 0.0  # the time spent waiting between tries

    def generate_json(self, system: str, prompt: str, schema: type[BaseModel]) -> str:
        """Return the model's answer as JSON text; temporary errors are retried and each wait is logged."""
        retrying = Retrying(
            retry=retry_if_exception_type(LLMTransientError),
            wait=wait_exponential(multiplier=self._retry_wait, max=60),
            stop=stop_after_attempt(self._max_retries),
            before_sleep=self._note_retry,
            reraise=True,
        )
        return retrying(self._call_once, system, prompt, schema)

    def _note_retry(self, retry_state: RetryCallState) -> None:
        """Say that a call is tried again and for how long it waits (a silent wait looks like a frozen run)."""
        wait = retry_state.next_action.sleep if retry_state.next_action else 0.0
        error = retry_state.outcome.exception() if retry_state.outcome else None
        self.retries += 1
        self.seconds_waited += wait
        logger.warning(
            "%s: waiting %.1fs before try %d of %d",
            error,
            wait,
            retry_state.attempt_number + 1,
            self._max_retries,
        )

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
