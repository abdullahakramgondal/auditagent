"""Run Agent 2 on the invoice and the purchase order of every generated case and score it.

Run:  python -m eval.agent2_eval --limit 5     (a few evenly spread cases)
      python -m eval.agent2_eval               (all cases; results made by the same code are reused)
      python -m eval.agent2_eval --provider ollama   (the small model on this computer)
Sends the text of synthetic documents to the LLM provider. Saved results are kept per model, each with
a fingerprint of the code that made it (agents, ingestion, schemas and the document generator): a
result made by other code is never reused (unless --reuse-old), and the report says how many cases
were really run now. The saved raw model answers let a failure be diagnosed without new calls.
"""

import argparse
import json
import statistics
import tempfile
import time
from pathlib import Path

from auditagent.agents.commercial_extractor import CommercialExtractor
from auditagent.config import get_settings
from auditagent.ingestion.pdf_parser import parse_pdf
from auditagent.llm.base import LLMError
from auditagent.llm.factory import build_provider
from auditagent.schemas.extraction import InvoiceResult, PurchaseOrderResult
from data.generator.commercial_pdf import write_invoice_pdf, write_po_pdf
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
from eval.agent2_scoring import KINDS, aggregate, score_document

AGENT2_CODE_FOLDERS = [*CODE_FOLDERS, ROOT / "data" / "generator"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="run only N evenly spread cases")
    parser.add_argument(
        "--pause",
        type=float,
        default=None,
        help="seconds to wait between live cases (default: 3 for Gemini, 0 for Ollama)",
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
    pause = args.pause if args.pause is not None else (3.0 if provider.name == "gemini" else 0.0)
    fingerprint = code_fingerprint(AGENT2_CODE_FOLDERS)
    extractor = CommercialExtractor(provider)

    cache_dir = RESULTS_DIR / f"agent2_{_safe(provider.model)}"
    cache_dir.mkdir(parents=True, exist_ok=True)
    specs = _pick(sorted((ROOT / "data" / "specs").glob("*.json")), args.limit)

    scored, seconds, calls, wrong_lines, issue_lines = [], [], [], [], []
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
                invoice_pdf = write_invoice_pdf(spec, Path(tmp) / f"{case_id}_invoice.pdf")
                po_pdf = write_po_pdf(spec, Path(tmp) / f"{case_id}_po.pdf")
                calls_before, answers_before = provider.calls, len(provider.raw_answers)
                started = time.perf_counter()
                print(f"{case_id}: running ...", flush=True)
                try:
                    invoice = extractor.extract_invoice(parse_pdf(invoice_pdf))
                    order = extractor.extract_purchase_order(parse_pdf(po_pdf))
                except LLMError as exc:
                    print(f"STOPPED at {case_id}: {exc}")
                    print("Run again later: finished cases are saved and will be reused.")
                    break
                saved = {
                    "case_id": case_id,
                    "code_hash": fingerprint,
                    "seconds": round(time.perf_counter() - started, 1),
                    "llm_calls": provider.calls - calls_before,
                    "invoice_result": invoice.model_dump(mode="json"),
                    "po_result": order.model_dump(mode="json"),
                    "raw_answers": provider.raw_answers[answers_before:],
                }
                cache_file.write_text(json.dumps(saved, indent=2))
                ran += 1
                print(f"{case_id}: done in {saved['seconds']}s, {saved['llm_calls']} model calls")
                time.sleep(pause)

            invoice = InvoiceResult.model_validate(saved["invoice_result"])
            order = PurchaseOrderResult.model_validate(saved["po_result"])
            documents = {
                "invoice": (spec["invoice"], invoice.invoice, invoice.issues),
                "purchase_order": (spec["purchase_order"], order.purchase_order, order.issues),
            }
            case_score = {}
            for kind, (gold, data, issues) in documents.items():
                entry = score_document(kind, gold, data, issues)
                case_score[kind] = entry
                if entry["status"] == "wrong":
                    for field, (expected, got) in entry["differences"].items():
                        wrong_lines.append((case_id, kind, field, expected, got))
                for issue in issues:
                    state = "extracted" if data is not None else "REFUSED"
                    issue_lines.append((case_id, kind, state, issue.clause_type, issue.reason))
            scored.append(case_score)
            seconds.append(saved["seconds"])
            calls.append(saved["llm_calls"])

    if not scored:
        return
    summary = aggregate(scored)
    print(
        f"\nAgent 2   provider: {provider.name}   model: {provider.model}   "
        f"cases scored: {len(scored)}"
    )
    print(f"code {fingerprint}: ran now {ran}, reused {reused} ({reused_old} from old code)")
    if ran == 0:
        print("NOTHING WAS RUN: every number below is a saved result (use --fresh to run again).")
    print(
        f"{'document':15} {'docs':>4} {'right':>5} {'wrong':>5} {'refus':>5} {'w/issue':>7} "
        f"{'recall':>6} {'prec':>5} {'field':>5}"
    )
    for name in (*KINDS, "ALL"):
        t = summary[name]
        print(
            f"{name:15} {t['docs']:>4} {t['correct']:>5} {t['wrong']:>5} {t['refused']:>5} "
            f"{t['correct_with_issues']:>7} {_fmt(t['recall']):>6} {_fmt(t['precision']):>5} "
            f"{_fmt(t['field_accuracy']):>5}"
        )
    print(
        f"average {sum(seconds) / len(seconds):.1f}s (median {statistics.median(seconds):.1f}s) "
        f"and {sum(calls) / len(calls):.1f} model calls per case"
    )
    print(f"\nWrong values ({len(wrong_lines)}):")
    for case_id, kind, field, expected, got in wrong_lines:
        print(f"   {case_id} {kind}.{field}: expected {expected}  got {got}")
    print(f"\nIssues ({len(issue_lines)}):")
    for case_id, kind, state, field, reason in issue_lines:
        print(f"   {case_id} {kind} [{state}] {field}: {reason}")

    out_path = RESULTS_DIR / f"agent2_{_safe(provider.model)}_summary.json"
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
                "wrong_values": wrong_lines,
                "issues": issue_lines,
            },
            indent=2,
        )
    )
    print("\nsaved", out_path)


if __name__ == "__main__":
    main()
