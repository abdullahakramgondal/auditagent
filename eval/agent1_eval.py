"""Run Agent 1 on contracts and score it against the answer key.

Run:  python -m eval.agent1_eval --limit 5     (Tier A: generated contracts, a few evenly spread)
      python -m eval.agent1_eval               (Tier A: all; finished ones are reused)
      python -m eval.agent1_eval --tier b      (Tier B: LLM-written PDFs in data/tier_b/pdf)
      python -m eval.agent1_eval --tier b --provider ollama   (the small model on this computer)
Sends contract text to the LLM provider: synthetic data only. Saved results are kept per model.
Each saved result also keeps the raw model answers (with the chunk ids sent and the seconds each call
took), so a failure can be diagnosed without new model calls.
"""

import argparse
import json
import re
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
TIER_B_DIR = ROOT / "data" / "tier_b"
CHUNK_ID_RE = re.compile(r"\[chunk_id: ([^\]]+)\]")


def _safe(name: str) -> str:
    """A model name as a folder or file name (a colon, as in qwen2.5:3b, is not allowed on Windows)."""
    return re.sub(r"[^A-Za-z0-9._-]", "-", name)


class CountingProvider:
    """Wraps a provider: counts the model calls and keeps every raw answer for later diagnosis."""

    def __init__(self, inner):
        self._inner = inner
        self.name = inner.name
        self.model = inner.model
        self.calls = 0
        self.raw_answers: list[dict] = []

    def generate_json(self, system, prompt, schema):
        self.calls += 1
        started = time.perf_counter()
        raw = self._inner.generate_json(system, prompt, schema)
        seconds = round(time.perf_counter() - started, 1)
        print(f"    call {self.calls}: {seconds}s", flush=True)
        self.raw_answers.append({
            "task": prompt[:60],
            "chunk_ids": CHUNK_ID_RE.findall(prompt),
            "seconds": seconds,
            "raw": raw,
        })
        return raw


def _pick(specs: list[Path], limit: int | None) -> list[Path]:
    if not limit or limit >= len(specs):
        return specs
    step = max(1, len(specs) // limit)
    return specs[::step][:limit]


def _fmt(value) -> str:
    return "-" if value is None else f"{value:.2f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", choices=["a", "b"], default="a",
                        help="a: generated contracts, b: LLM-written contracts in data/tier_b")
    parser.add_argument("--limit", type=int, default=None, help="run only N evenly spread contracts")
    parser.add_argument("--pause", type=float, default=None,
                        help="seconds to wait between live contracts (default: 6 for Gemini, 0 for Ollama)")
    parser.add_argument("--fresh", action="store_true", help="ignore saved results and call the model again")
    parser.add_argument("--provider", choices=["gemini", "ollama"], default=None,
                        help="use this provider instead of LLM_PROVIDER from .env")
    parser.add_argument("--model", default=None, help="override the model of the chosen provider for this run")
    args = parser.parse_args()

    settings = get_settings()
    updates = {}
    if args.provider:
        updates["llm_provider"] = args.provider
    if args.model:
        chosen = updates.get("llm_provider", settings.llm_provider)
        updates["ollama_model" if chosen == "ollama" else "gemini_model"] = args.model
    if updates:
        settings = settings.model_copy(update=updates)
    provider = CountingProvider(build_provider(settings))
    pause = args.pause if args.pause is not None else (6.0 if provider.name == "gemini" else 0.0)
    embedder = SentenceTransformerEmbedder()
    embedder.embed(["warm up"])  # load the model before any timing starts
    extractor = LegalExtractor(provider, embedder)

    tag = "agent1" if args.tier == "a" else "agent1_tierb"
    cache_dir = RESULTS_DIR / f"{tag}_{_safe(provider.model)}"
    cache_dir.mkdir(parents=True, exist_ok=True)
    if args.tier == "a":
        all_specs = sorted((ROOT / "data" / "specs").glob("*.json"))
    else:
        all_specs = [p for p in sorted((TIER_B_DIR / "specs").glob("*.json"))
                     if (TIER_B_DIR / "pdf" / f"{p.stem}.pdf").exists()]
    specs = _pick(all_specs, args.limit)
    if not specs:
        raise SystemExit("No contracts to run (for Tier B: put PDFs in data/tier_b/pdf/<id>.pdf).")

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
                if args.tier == "a":
                    out = build_case(spec_path, tmp)
                    gold_sources = json.loads((out / "expected.json").read_text())["rule_sources"]
                    pdf_path = out / "contract.pdf"
                else:
                    gold_sources = {}
                    pdf_path = TIER_B_DIR / "pdf" / f"{case_id}.pdf"
                doc = parse_pdf(pdf_path)
                calls_before, answers_before = provider.calls, len(provider.raw_answers)
                started = time.perf_counter()
                print(f"{case_id}: running ...", flush=True)
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
                    "raw_answers": provider.raw_answers[answers_before:],
                }
                cache_file.write_text(json.dumps(saved, indent=2))
                print(f"{case_id}: done in {saved['seconds']}s, {saved['llm_calls']} model calls")
                time.sleep(pause)

            result = AgentOneResult.model_validate(saved["result"])
            case_score = score_case(spec, result, saved["gold_sources"])
            scored.append(case_score)
            seconds.append(saved["seconds"])
            calls.append(saved["llm_calls"])
            for kind, entry in case_score.items():
                if entry["status"] in ("wrong", "refused", "silent_miss", "spurious"):
                    problems.append({
                        "case": case_id, "clause": kind, "status": entry["status"],
                        "wrong_fields": [f for f, ok in entry.get("fields", {}).items() if not ok],
                        "gold": next((r for r in spec["rules"] if r["clause_type"] == kind), None),
                        "got": next((r.model_dump(mode="json", exclude={"source", "deadline_source"})
                                     for r in result.contract.rules if r.clause_type == kind), None),
                    })
            issues += [{"case": case_id, "clause": i.clause_type, "reason": i.reason, "quote": i.quote}
                       for i in result.issues]

    if not scored:
        return
    summary = aggregate(scored)
    print(f"\ntier {args.tier.upper()}   provider: {provider.name}   model: {provider.model}   "
          f"contracts scored: {len(scored)}")
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
        print(f"   {p['case']} {p['clause']}: {p['status']}  wrong fields: {p['wrong_fields']}")
        print(f"       gold: {p['gold']}")
        print(f"       got : {p['got']}")
    print(f"\nRefusals and issues ({len(issues)}):")
    for i in issues:
        print(f"   {i['case']} [{i['clause']}] {i['reason']}")
        if i["quote"]:
            print(f"       quote: {i['quote']}")

    out_path = RESULTS_DIR / f"{tag}_{_safe(provider.model)}_summary.json"
    out_path.write_text(json.dumps({
        "tier": args.tier, "provider": provider.name, "model": provider.model, "contracts": len(scored),
        "summary": summary,
        "avg_seconds": round(sum(seconds) / len(seconds), 1), "median_seconds": statistics.median(seconds),
        "avg_calls": round(sum(calls) / len(calls), 1),
        "problems": problems, "issues": issues,
    }, indent=2))
    print("\nsaved", out_path)


if __name__ == "__main__":
    main()