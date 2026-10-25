"""Manual check that the model name and structured output work for a provider.

Run from the project root:  python -m auditagent.llm.smoke                     (provider from .env)
                            python -m auditagent.llm.smoke --provider ollama   (small model on this computer)
Sends one tiny synthetic sentence. Never put a real document here.
"""

import argparse
import time

from pydantic import BaseModel, Field

from auditagent.config import get_settings
from auditagent.llm.base import generate_structured
from auditagent.llm.factory import build_provider


class PenaltyDemo(BaseModel):
    percent: int = Field(ge=1, le=100)
    deadline: str


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--provider",
        choices=["gemini", "ollama"],
        default=None,
        help="use this provider instead of LLM_PROVIDER from .env",
    )
    args = parser.parse_args()

    settings = get_settings()
    if args.provider:
        settings = settings.model_copy(update={"llm_provider": args.provider})
    provider = build_provider(settings)
    print(f"provider={provider.name} model={provider.model}")

    names = provider.list_models()
    shown = [n for n in names if provider.name != "gemini" or n.startswith("gemini")]
    print(f"\nModels this provider can use for text ({len(shown)}):")
    for n in shown:
        print("  ", n, "  <-- configured" if n == provider.model else "")
    if provider.model not in names:
        print(
            f"\nWARNING: '{provider.model}' is not in the list. Set GEMINI_MODEL or OLLAMA_MODEL in .env "
            f"(for Ollama: ollama pull {provider.model})."
        )
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
