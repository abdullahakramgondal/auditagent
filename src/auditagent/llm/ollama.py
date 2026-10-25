"""Ollama provider: a small model running on this computer (no API key, no cost, nothing leaves the machine)."""

import httpx
from pydantic import BaseModel

from auditagent.llm.base import LLMError


class OllamaProvider:
    """Talks to a local Ollama server through /api/chat, with the JSON schema as the output format."""

    name = "ollama"

    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        num_ctx: int = 8192,
        timeout: float = 600.0,
        client: httpx.Client | None = None,
    ):
        self.model = model
        self._base_url = base_url.rstrip("/")
        self._num_ctx = num_ctx
        self._client = client or httpx.Client(timeout=timeout)

    def generate_json(self, system: str, prompt: str, schema: type[BaseModel]) -> str:
        """Return the model's answer as JSON text (an empty string if it said nothing)."""
        body = {
            "model": self.model,
            "stream": False,
            "format": schema.model_json_schema(),
            "options": {"temperature": 0, "num_ctx": self._num_ctx},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        data = self._request("POST", "/api/chat", json=body)
        return (data.get("message") or {}).get("content") or ""

    def list_models(self) -> list[str]:
        """Models downloaded on this computer (for example 'qwen2.5:3b')."""
        data = self._request("GET", "/api/tags")
        return sorted(m["name"] for m in data.get("models", []))

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """One HTTP call to the Ollama server; every failure becomes an LLMError with the fix in it."""
        try:
            response = self._client.request(method, f"{self._base_url}{path}", **kwargs)
        except httpx.ConnectError as exc:
            raise LLMError(
                f"Cannot reach Ollama at {self._base_url}. Is it running? Start it with: ollama serve"
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMError(
                "Ollama did not answer in time (a small model is slow on this computer). "
                "Raise OLLAMA_TIMEOUT in .env."
            ) from exc
        if response.status_code == 404:
            raise LLMError(
                f"Ollama does not have the model {self.model!r}. Download it with: ollama pull {self.model}"
            )
        if response.status_code != 200:
            raise LLMError(f"Ollama error {response.status_code}: {response.text[:200]}")
        return response.json()
