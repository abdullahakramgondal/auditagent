"""Run Agent 1 on contracts and score it against the answer key.

Run:  python -m eval.agent1_eval --limit 5     (Tier A: generated contracts, a few evenly spread)
      python -m eval.agent1_eval               (Tier A: all; results made by the same code are reused)
      python -m eval.agent1_eval --tier b      (Tier B: LLM-written PDFs in data/tier_b/pdf)
      python -m eval.agent1_eval --tier b --provider ollama   (the small model on this computer)
Sends contract text to the LLM provider: synthetic data only. Saved results are kept per model.
Each saved result keeps the raw model answers (with the chunk ids sent and the seconds each call
took) and a fingerprint of the Agent 1 code that made it. A result made by other code is never
reused (unless --reuse-old), and the report says how many contracts were really run now.
"""

import argparse
import hashlib
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
# The folders whose code decides what Agent 1 answers (the LLM provider code does not).
CODE_FOLDERS = [ROOT / "src" / "auditagent" / name for name in ("agents", "ingestion", "schemas")]


def _safe(name: str) -> str:
    """A model name as a folder or file name (a colon, as in qwen2.5:3b, is not allowed on Windows)."""
    return re.sub(r"[^A-Za-z0-9._-]", "-", name)


def code_fingerprint(folders: list[Path]) -> str:
    """A short hash of every .py file in the folders. Any edit, even formatting, changes it.

    Line endings are ignored so that a Windows and a Linux checkout of the same code agree.
    """
    digest = hashlib.sha256()
    for folder in folders:
        for path in sorted(folder.rglob("*.py")):
            digest.update(f"{folder.name}/{path.relative_to(folder).as_posix()}\n".encode())
            digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()[:12]


def cache_state(saved: dict, fingerprint: str) -> str:
    """ "same" if the current code made this saved result, otherwise "old".

    A result saved before fingerprints existed has no code_hash and counts as old.
    """
    return "same" if saved.get("code_hash") == fingerprint else "old"


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
        self.raw_answers.append(
            {
                "task": prompt[:60],
                "chunk_ids": CHUNK_ID_RE.findall(prompt),
                "seconds": seconds,
                "raw": raw,
            }
        )
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
    parser.add_argument(
        "--tier",
        choices=["a", "b"],
        default="a",
        help="a: generated contracts, b: LLM-written contracts in data/tier_b",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="run only N evenly spread contracts"
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=None,
        help="seconds to wait between live contracts (default: 6 for Gemini, 0 for Ollama)",
    )
    parser.add_argument(
        "--fresh", action="store_true", help="ignore saved results and call the model again"
    )
    parser.add_argument(
        "--reuse-old",
        action="store_true",
        help="also reuse saved results that other code made (they are marked in the output)",
    )
    parser.add_argument(
        "--provider",
        choices=["gemini", "ollama"],
        default=None,
        help="use this provider instead of LLM_PROVIDER from .env",
    )
    parser.add_argument(
        "--model", default=None, help="override the model of the chosen provider for this run"
    )
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
    fingerprint = code_fingerprint(CODE_FOLDERS)
    embedder = SentenceTransformerEmbedder()
    embedder.embed(["warm up"])  # load the model before any timing starts
    extractor = LegalExtractor(provider, embedder)

    tag = "agent1" if args.tier == "a" else "agent1_tierb"
    cache_dir = RESULTS_DIR / f"{tag}_{_safe(provider.model)}"
    cache_dir.mkdir(parents=True, exist_ok=True)
    if args.tier == "a":
        all_specs = sorted((ROOT / "data" / "specs").glob("*.json"))
    else:
        all_specs = [
            p
            for p in sorted((TIER_B_DIR / "specs").glob("*.json"))
            if (TIER_B_DIR / "pdf" / f"{p.stem}.pdf").exists()
        ]
    specs = _pick(all_specs, args.limit)
    if not specs:
        raise SystemExit("No contracts to run (for Tier B: put PDFs in data/tier_b/pdf/<id>.pdf).")

    scored, seconds, calls, problems, issues = [], [], [], [], []
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
                    "code_hash": fingerprint,
                    "seconds": round(time.perf_counter() - started, 1),
                    "llm_calls": provider.calls - calls_before,
                    "gold_sources": gold_sources,
                    "result": result.model_dump(mode="json"),
                    "raw_answers": provider.raw_answers[answers_before:],
                }
                cache_file.write_text(json.dumps(saved, indent=2))
                ran += 1
                print(f"{case_id}: done in {saved['seconds']}s, {saved['llm_calls']} model calls")
                time.sleep(pause)

            result = AgentOneResult.model_validate(saved["result"])
            case_score = score_case(spec, result, saved["gold_sources"])
            scored.append(case_score)
            seconds.append(saved["seconds"])
            calls.append(saved["llm_calls"])
            for kind, entry in case_score.items():
                if entry["status"] in ("wrong", "refused", "silent_miss", "spurious"):
                    problems.append(
                        {
                            "case": case_id,
                            "clause": kind,
                            "status": entry["status"],
                            "wrong_fields": [
                                f for f, ok in entry.get("fields", {}).items() if not ok
                            ],
                            "gold": next(
                                (r for r in spec["rules"] if r["clause_type"] == kind), None
                            ),
                            "got": next(
                                (
                                    r.model_dump(mode="json", exclude={"source", "deadline_source"})
                                    for r in result.contract.rules
                                    if r.clause_type == kind
                                ),
                                None,
                            ),
                        }
                    )
            issues += [
                {"case": case_id, "clause": i.clause_type, "reason": i.reason, "quote": i.quote}
                for i in result.issues
            ]

    if not scored:
        return
    summary = aggregate(scored)
    print(
        f"\ntier {args.tier.upper()}   provider: {provider.name}   model: {provider.model}   "
        f"contracts scored: {len(scored)}"
    )
    print(f"code {fingerprint}: ran now {ran}, reused {reused} ({reused_old} from old code)")
    if ran == 0:
        print("NOTHING WAS RUN: every number below is a saved result (use --fresh to run again).")
    print(
        f"{'clause':16} {'gold':>4} {'right':>5} {'wrong':>5} {'refus':>5} {'silent':>6} {'spur':>4}  {'recall':>6} {'prec':>5}"
    )
    for name in (*KINDS, "ALL"):
        t = summary[name]
        print(
            f"{name:16} {t['gold']:>4} {t['correct']:>5} {t['wrong']:>5} {t['refused']:>5} {t['silent_miss']:>6} "
            f"{t['spurious']:>4}  {_fmt(t['recall']):>6} {_fmt(t['precision']):>5}"
        )
    a = summary["ALL"]
    print(
        f"field accuracy {_fmt(a['field_accuracy'])}   page accuracy {_fmt(a['page_accuracy'])}   "
        f"quote accuracy {_fmt(a['quote_accuracy'])}"
    )
    print(
        f"average {sum(seconds) / len(seconds):.1f}s (median {statistics.median(seconds):.1f}s) "
        f"and {sum(calls) / len(calls):.1f} model calls per contract"
    )
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
    out_path.write_text(
        json.dumps(
            {
                "tier": args.tier,
                "provider": provider.name,
                "model": provider.model,
                "code_hash": fingerprint,
                "contracts": len(scored),
                "ran_now": ran,
                "reused": reused,
                "reused_from_old_code": reused_old,
                "summary": summary,
                "avg_seconds": round(sum(seconds) / len(seconds), 1),
                "median_seconds": statistics.median(seconds),
                "avg_calls": round(sum(calls) / len(calls), 1),
                "problems": problems,
                "issues": issues,
            },
            indent=2,
        )
    )
    print("\nsaved", out_path)


if __name__ == "__main__":
    main()
