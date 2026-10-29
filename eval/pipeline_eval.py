"""Run the whole pipeline (Agent 1, Agent 2, rule engine) on every generated case and score it.

Run:  python -m eval.pipeline_eval --limit 5     (a few evenly spread cases)
      python -m eval.pipeline_eval               (all cases; results made by the same code are reused)
      python -m eval.pipeline_eval --provider ollama
Sends the text of synthetic documents to the LLM provider. Each case: 4 Agent 1 calls and 2 Agent 2 calls.
Saved results are kept per model with a fingerprint of the code (agents, ingestion, schemas, rules,
pipeline and the document generator): a result made by other code is never reused (unless --reuse-old).
The number that must stay at 0 is "wrong": a verdict that differs from the answer key.
The hand-made anchor case_001 has no category: it is scored as "anchor".
"""

import argparse
import json
import statistics
import tempfile
import time

from auditagent.agents.commercial_extractor import CommercialExtractor
from auditagent.agents.legal_extractor import LegalExtractor
from auditagent.config import get_settings
from auditagent.ingestion.embedder import SentenceTransformerEmbedder
from auditagent.llm.base import LLMError
from auditagent.llm.factory import build_provider
from auditagent.pipeline.run import AuditReport, audit_files
from data.generator.build_case import build_case
from eval.agent1_eval import (
    CODE_FOLDERS,
    RESULTS_DIR,
    ROOT,
    CountingProvider,
    _fmt,
    _pick,
    _safe,
    cache_state,
    code_fingerprint,
)
from eval.pipeline_scoring import aggregate, score_case

PIPELINE_CODE_FOLDERS = [
    *CODE_FOLDERS,
    ROOT / "src" / "auditagent" / "rules",
    ROOT / "src" / "auditagent" / "pipeline",
    ROOT / "data" / "generator",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="run only N evenly spread cases")
    parser.add_argument(
        "--pause",
        type=float,
        default=None,
        help="seconds to wait between live cases (default: 4 for Gemini, 0 for Ollama)",
    )
    parser.add_argument(
        "--fresh", action="store_true", help="ignore saved results and call the model again"
    )
    parser.add_argument(
        "--reuse-old",
        action="store_true",
        help="also reuse saved results that other code made (they are marked in the output)",
    )
    parser.add_argument("--provider", choices=["gemini", "ollama"], default=None)
    parser.add_argument("--model", default=None, help="override the model of the chosen provider")
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
    pause = args.pause if args.pause is not None else (4.0 if provider.name == "gemini" else 0.0)
    fingerprint = code_fingerprint(PIPELINE_CODE_FOLDERS)
    embedder = SentenceTransformerEmbedder()
    embedder.embed(["warm up"])  # load the model before any timing starts
    legal = LegalExtractor(provider, embedder)
    commercial = CommercialExtractor(provider)

    cache_dir = RESULTS_DIR / f"pipeline_{_safe(provider.model)}"
    cache_dir.mkdir(parents=True, exist_ok=True)
    specs = _pick(sorted((ROOT / "data" / "specs").glob("*.json")), args.limit)

    scored, seconds, calls, problems = [], [], [], []
    ran = reused = reused_old = 0
    with tempfile.TemporaryDirectory() as tmp:
        for spec_path in specs:
            spec = json.loads(spec_path.read_text())
            case_id = spec["case_id"]
            cache_file = cache_dir / f"{case_id}.json"

            saved = None
            if cache_file.exists() and not args.fresh:
                cached = json.loads(cache_file.read_text())
                if cache_state(cached, fingerprint) == "same":
                    saved = cached
                    reused += 1
                    print(f"{case_id}: saved result reused")
                elif args.reuse_old:
                    saved = cached
                    reused += 1
                    reused_old += 1
                    print(
                        f"{case_id}: REUSED A RESULT FROM OLD CODE "
                        f"({cached.get('code_hash', 'no fingerprint')})"
                    )
                else:
                    print(f"{case_id}: saved result is from other code, running again")

            if saved is None:
                out = build_case(spec_path, tmp)
                calls_before, answers_before = provider.calls, len(provider.raw_answers)
                started = time.perf_counter()
                print(f"{case_id}: running ...", flush=True)
                try:
                    report = audit_files(
                        out / "contract.pdf", out / "po.pdf", out / "invoice.pdf", legal, commercial
                    )
                except LLMError as exc:
                    print(f"STOPPED at {case_id}: {exc}")
                    print("Run again later: finished cases are saved and will be reused.")
                    break
                saved = {
                    "case_id": case_id,
                    "code_hash": fingerprint,
                    "seconds": round(time.perf_counter() - started, 1),
                    "llm_calls": provider.calls - calls_before,
                    "report": report.model_dump(mode="json"),
                    "raw_answers": provider.raw_answers[answers_before:],
                }
                cache_file.write_text(json.dumps(saved, indent=2))
                ran += 1
                print(f"{case_id}: done in {saved['seconds']}s, {saved['llm_calls']} model calls")
                time.sleep(pause)

            report = AuditReport.model_validate(saved["report"])
            category = spec.get("category", "anchor")
            entry = {**score_case(spec["expected"], report.result), "category": category}
            scored.append(entry)
            seconds.append(saved["seconds"])
            calls.append(saved["llm_calls"])
            if entry["outcome"] != "correct" or entry["reasons"]:
                problems.append((case_id, entry, report.result))

    if not scored:
        return
    summary = aggregate(scored)
    print(
        f"\nPipeline   provider: {provider.name}   model: {provider.model}   "
        f"cases scored: {len(scored)}"
    )
    print(f"code {fingerprint}: ran now {ran}, reused {reused} ({reused_old} from old code)")
    if ran == 0:
        print("NOTHING WAS RUN: every number below is a saved result (use --fresh to run again).")
    print(
        f"{'category':18} {'cases':>5} {'right':>5} {'review':>6} {'WRONG':>5} "
        f"{'w/reason':>8} {'acc':>5}"
    )
    for name, t in sorted(summary.items(), key=lambda kv: (kv[0] == "ALL", kv[0])):
        print(
            f"{name:18} {t['cases']:>5} {t['correct']:>5} {t['review']:>6} {t['wrong']:>5} "
            f"{t['correct_with_reasons']:>8} {_fmt(t['accuracy']):>5}"
        )
    print(
        f"average {sum(seconds) / len(seconds):.1f}s (median {statistics.median(seconds):.1f}s) "
        f"and {sum(calls) / len(calls):.1f} model calls per case"
    )

    print(f"\nCases that are not clean ({len(problems)}):")
    for case_id, entry, result in problems:
        failed = [name for name, ok in entry["checks"].items() if not ok]
        print(
            f"   {case_id} [{entry['category']}] {entry['outcome'].upper()}: "
            f"got {entry['status']}, expected {entry['expected_status']}, failed checks: {failed}"
        )
        for reason in result.review_reasons:
            print(f"       reason: {reason}")

    out_path = RESULTS_DIR / f"pipeline_{_safe(provider.model)}_summary.json"
    out_path.write_text(
        json.dumps(
            {
                "provider": provider.name,
                "model": provider.model,
                "code_hash": fingerprint,
                "cases": len(scored),
                "ran_now": ran,
                "reused": reused,
                "reused_from_old_code": reused_old,
                "summary": summary,
                "avg_seconds": round(sum(seconds) / len(seconds), 1),
                "median_seconds": statistics.median(seconds),
                "avg_calls": round(sum(calls) / len(calls), 1),
                "not_clean": [
                    {
                        "case": case_id,
                        "category": entry["category"],
                        "outcome": entry["outcome"],
                        "checks": entry["checks"],
                    }
                    for case_id, entry, _ in problems
                ],
            },
            indent=2,
        )
    )
    print("\nsaved", out_path)


if __name__ == "__main__":
    main()
