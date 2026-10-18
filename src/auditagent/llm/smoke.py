"""Manual check that the API key, the model name and structured output all work.

Run from the project root:  python -m auditagent.llm.smoke
Sends one tiny synthetic sentence. Never put a real document here.
"""

import time

from pydantic import BaseModel, Field

from auditagent.config import get_settings
from auditagent.llm.base import generate_structured
from auditagent.llm.factory import build_provider


class PenaltyDemo(BaseModel):
    percent: int = Field(ge=1, le=100)
    deadline: str


def main() -> None:
    settings = get_settings()
    provider = build_provider(settings)
    print(f"provider={provider.name} model={provider.model}")

    names = provider.list_models()
    gemini = [n for n in names if n.startswith("gemini")]
    print(f"\nModels this key can use for text ({len(gemini)}):")
    for n in gemini:
        print("  ", n, "  <-- configured" if n == provider.model else "")
    if provider.model not in names:
        print(f"\nWARNING: '{provider.model}' is not in the list. Set GEMINI_MODEL in .env.")
        return

    started = time.perf_counter()
    result = generate_structured(
        provider,
        system="You extract contract rules. Answer with JSON only.",
        prompt="Clause: 'If delivery is later than 15 October 2026, a penalty of 10% shall apply.'",
        schema=PenaltyDemo,
    )
    print(f"\nStructured answer: {result}  ({time.perf_counter() - started:.1f}s)")


if __name__ == "__main__":
    main()