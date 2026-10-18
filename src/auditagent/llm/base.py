"""One small interface for every LLM provider, plus the structured-output loop."""

from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """Anything that went wrong while talking to a model."""


class LLMTransientError(LLMError):
    """Rate limit or temporary outage. Worth retrying after a wait."""


class LLMOutputError(LLMError):
    """The model never produced output that passes our schema."""


class LLMProvider(Protocol):
    name: str
    model: str

    def generate_json(self, system: str, prompt: str, schema: type[BaseModel]) -> str:
        """Return the model's answer as JSON text."""
        ...


def _short_errors(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors()[:5]:
        where = ".".join(str(p) for p in err["loc"]) or "(root)"
        parts.append(f"{where}: {err['msg']}")
    return "; ".join(parts)


def generate_structured(
    provider: LLMProvider,
    system: str,
    prompt: str,
    schema: type[T],
    max_attempts: int = 3,
) -> T:
    """Ask for JSON, let the schema inspect it, and send it back with the reasons if rejected."""
    current = prompt
    last_error = ""
    for _ in range(max_attempts):
        raw = provider.generate_json(system, current, schema)
        try:
            return schema.model_validate_json(raw)
        except ValidationError as exc:
            last_error = _short_errors(exc)
            current = (
                f"{prompt}\n\nYour previous answer was rejected.\n"
                f"Problems: {last_error}\n"
                f"Previous answer: {raw[:1500]}\n"
                "Return corrected JSON only."
            )
    raise LLMOutputError(f"No valid output after {max_attempts} attempts. Last problems: {last_error}")