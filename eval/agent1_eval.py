"""Run Agent 1 on the synthetic contracts and score it against the answer key.

Run:  python -m eval.agent1_eval --limit 5     (a few contracts, evenly spread, to try it out)
      python -m eval.agent1_eval               (all contracts; finished ones are reused)
Sends contract text to the LLM provider: synthetic data only.
"""

import argparse
import json
import statistics
import tempfile
import time
from pathlib import Path

from auditagent.agents.legal_extractor import LegalExtractor
from auditagent.config import get_settings
from auditagent.ingestion.embedder import SentenceTransformerEmbedder
from auditagent.ingestion.pdf_parser import parse_pdf
from auditagent.llm.base import LLMError
from auditagent.llm.factory import build_provider
from auditagent.schemas.extraction import AgentOneResult
from data.generator.build_case import build_case
from eval.agent1_scoring import KINDS, aggregate, score_case

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "eval" / "results"


class CountingProvider:
    """Wraps a provider and counts how many model calls were made."""

    def __init__(self, inner):
        self._inner = inner
        self.name = inner.name
        self.model = inner.model
        self.calls = 0

    def generate_json(self, system, prompt, schema):
        self.calls += 1
        return self._inner.generate_json(system, prompt, schema)


def _pick(specs: list[Path], limit: int | None) -> list[Path]:
    if not limit or limit >= len(specs):
        return specs
    step = max(1, len(specs) // limit)
    return specs[::step][:limit]


def _fmt(value) -> str:
    return "-" if value is None else f"{value:.2f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="run only N evenly spread contracts")
    parser.add_argument("--pause", type=float, default=6.0, help="seconds to wait between live contracts")
    parser.add_argument("--fresh", action="store_true", help="ignore saved results and call the model again")
    parser.add_argument("--model", default=None, help="override GEMINI_MODEL for this run")
    args = parser.parse_args()

    settings = get_settings()
    if args.model:
        settings = settings.model_copy(update={"gemini_model": args.model})
    provider = CountingProvider(build_provider(settings))
    embedder = SentenceTransformerEmbedder()
    embedder.embed(["warm up"])  # load the model before any timing starts
    extractor = LegalExtractor(provider, embedder)

    cache_dir = RESULTS_DIR / f"agent1_{provider.model}"
    cache_dir.mkdir(parents=True, exist_ok=True)
    specs = _pick(sorted((ROOT / "data" / "specs").glob("*.json")), args.limit)

    scored, seconds, calls, problems, issues = [], [], [], [], []
    with tempfile.TemporaryDirectory() as tmp:
        for spec_path in specs:
            spec = json.loads(spec_path.read_text())
            case_id = spec["case_id"]
            cache_file = cache_dir / f"{case_id}.json"

            if cache_file.exists() and not args.fresh:
                saved = json.loads(cache_file.read_text())
                print(f"{case_id}: saved result reused")
            else:
                out = build_case(spec_path, tmp)
                gold_sources = json.loads((out / "expected.json").read_text())["rule_sources"]
                doc = parse_pdf(out / "contract.pdf")
                calls_before, started = provider.calls, time.perf_counter()
                try:
                    result = extractor.extract(doc)
                except LLMError as exc:
                    print(f"STOPPED at {case_id}: {exc}")
                    print("Run again later: finished contracts are saved and will be reused.")
                    break
                saved = {
                    "case_id": case_id,
                    "seconds": round(time.perf_counter() - started, 1),
                    "llm_calls": provider.calls - calls_before,
                    "gold_sources": gold_sources,
                    "result": result.model_dump(mode="json"),
                }
                cache_file.write_text(json.dumps(saved, indent=2))
                print(f"{case_id}: done in {saved['seconds']}s, {saved['llm_calls']} model calls")
                time.sleep(args.pause)

            result = AgentOneResult.model_validate(saved["result"])
            case_score = score_case(spec, result, saved["gold_sources"])
            scored.append(case_score)
            seconds.append(saved["seconds"])
            calls.append(saved["llm_calls"])
            for kind, entry in case_score.items():
                if entry["status"] in ("wrong", "refused", "silent_miss", "spurious"):
                    wrong_fields = [f for f, ok in entry.get("fields", {}).items() if not ok]
                    problems.append({"case": case_id, "clause": kind, "status": entry["status"], "wrong_fields": wrong_fields})
            issues += [{"case": case_id, "clause": i.clause_type, "reason": i.reason} for i in result.issues]

    if not scored:
        return
    summary = aggregate(scored)
    print(f"\nmodel: {provider.model}   contracts scored: {len(scored)}")
    print(f"{'clause':16} {'gold':>4} {'right':>5} {'wrong':>5} {'refus':>5} {'silent':>6} {'spur':>4}  {'recall':>6} {'prec':>5}")
    for name in (*KINDS, "ALL"):
        t = summary[name]
        print(f"{name:16} {t['gold']:>4} {t['correct']:>5} {t['wrong']:>5} {t['refused']:>5} {t['silent_miss']:>6} "
              f"{t['spurious']:>4}  {_fmt(t['recall']):>6} {_fmt(t['precision']):>5}")
    a = summary["ALL"]
    print(f"field accuracy {_fmt(a['field_accuracy'])}   page accuracy {_fmt(a['page_accuracy'])}   "
          f"quote accuracy {_fmt(a['quote_accuracy'])}")
    print(f"average {sum(seconds) / len(seconds):.1f}s (median {statistics.median(seconds):.1f}s) "
          f"and {sum(calls) / len(calls):.1f} model calls per contract")
    print(f"\nProblems ({len(problems)}):")
    for p in problems:
        print("  ", p)
    print(f"\nRefusals and issues ({len(issues)}):")
    for i in issues:
        print("  ", i)

    out_path = RESULTS_DIR / f"agent1_{provider.model}_summary.json"
    out_path.write_text(json.dumps({
        "model": provider.model, "contracts": len(scored), "summary": summary,
        "avg_seconds": round(sum(seconds) / len(seconds), 1), "median_seconds": statistics.median(seconds),
        "avg_calls": round(sum(calls) / len(calls), 1),
        "problems": problems, "issues": issues,
    }, indent=2))
    print("\nsaved", out_path)


if __name__ == "__main__":
    main()