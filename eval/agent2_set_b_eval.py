"""Run Agent 2 on the documents of commercial set B and score it against their answer keys (TODO item 73).

Run:  python -m eval.agent2_set_b_eval
      python -m eval.agent2_set_b_eval --provider ollama   (the small model on this computer)
The documents must be frozen in git BEFORE this runs, and it is run ONCE: never edit a document after seeing
the result. Right after the first run copy eval/results/agent2_setb_<model> to a folder with "first_run" in
its name, because a later fix means the documents are no longer unseen.
Each document has one shape (see "shape" in its spec), so a failure has one cause.
Saved results carry a code fingerprint like the other evaluations: a result made by other code is not reused.
"""

import argparse
import json
import statistics
import time

from auditagent.agents.commercial_extractor import CommercialExtractor
from auditagent.config import get_settings
from auditagent.ingestion.pdf_parser import parse_pdf
from auditagent.llm.base import LLMError
from auditagent.llm.factory import build_provider
from auditagent.schemas.extraction import InvoiceResult, PurchaseOrderResult
from eval.agent1_eval import (
    RESULTS_DIR,
    ROOT,
    CountingProvider,
    _fmt,
    _safe,
    cache_state,
    code_fingerprint,
)
from eval.agent2_eval import AGENT2_CODE_FOLDERS
from eval.agent2_scoring import KINDS, aggregate, score_document

SET_DIR = ROOT / "data" / "commercial_b"
RESULT_CLASSES = {"invoice": InvoiceResult, "purchase_order": PurchaseOrderResult}


def document_of(kind: str, result):
    """The extracted document of a result: the invoice, or the purchase order (None if it was refused)."""
    return result.invoice if kind == "invoice" else result.purchase_order


def run_document(extractor: CommercialExtractor, kind: str, pdf_path):
    """Run Agent 2 on one PDF as an invoice or as a purchase order."""
    doc = parse_pdf(pdf_path)
    if kind == "invoice":
        return extractor.extract_invoice(doc)
    return extractor.extract_purchase_order(doc)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pause",
        type=float,
        default=None,
        help="seconds to wait between live documents (default: 3 for Gemini, 0 for Ollama)",
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

    cache_dir = RESULTS_DIR / f"agent2_setb_{_safe(provider.model)}"
    cache_dir.mkdir(parents=True, exist_ok=True)
    spec_paths = [
        path
        for path in sorted((SET_DIR / "specs").glob("*.json"))
        if (SET_DIR / "pdf" / f"{path.stem}.pdf").exists()
    ]
    if not spec_paths:
        raise SystemExit("No documents to run (put the PDFs in data/commercial_b/pdf/<id>.pdf).")

    scored, rows, seconds, wrong_lines, issue_lines = [], [], [], [], []
    ran = reused = reused_old = 0
    for spec_path in spec_paths:
        spec = json.loads(spec_path.read_text())
        case_id, kind = spec["case_id"], spec["kind"]
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
            answers_before = len(provider.raw_answers)
            started = time.perf_counter()
            print(f"{case_id}: running ...", flush=True)
            try:
                result = run_document(extractor, kind, SET_DIR / "pdf" / f"{case_id}.pdf")
            except LLMError as exc:
                print(f"STOPPED at {case_id}: {exc}")
                print("Run again later: finished documents are saved and will be reused.")
                break
            saved = {
                "case_id": case_id,
                "code_hash": fingerprint,
                "seconds": round(time.perf_counter() - started, 1),
                "result": result.model_dump(mode="json"),
                "raw_answers": provider.raw_answers[answers_before:],
            }
            cache_file.write_text(json.dumps(saved, indent=2))
            ran += 1
            print(f"{case_id}: done in {saved['seconds']}s")
            time.sleep(pause)

        result = RESULT_CLASSES[kind].model_validate(saved["result"])
        data = document_of(kind, result)
        entry = score_document(kind, spec["document"], data, result.issues)
        scored.append({kind: entry})
        rows.append((case_id, kind, entry["status"], spec["shape"]))
        seconds.append(saved["seconds"])
        for field, (expected, got) in entry.get("differences", {}).items():
            wrong_lines.append((case_id, field, expected, got))
        for issue in result.issues:
            state = "extracted" if data is not None else "REFUSED"
            issue_lines.append((case_id, state, issue.clause_type, issue.reason))

    if not scored:
        return
    summary = aggregate(scored)
    print(f"\nAgent 2 on commercial set B   provider: {provider.name}   model: {provider.model}")
    print(f"code {fingerprint}: ran now {ran}, reused {reused} ({reused_old} from old code)")
    if ran == 0:
        print("NOTHING WAS RUN: every number below is a saved result (use --fresh to run again).")
    print(f"\n{'case':6} {'document':15} {'result':8} shape")
    for case_id, kind, status, shape in rows:
        print(f"{case_id:6} {kind:15} {status:8} {shape}")
    print(
        f"\n{'document':15} {'docs':>4} {'right':>5} {'wrong':>5} {'refus':>5} {'w/issue':>7} "
        f"{'recall':>6} {'prec':>5} {'field':>5}"
    )
    for name in (*KINDS, "ALL"):
        t = summary[name]
        print(
            f"{name:15} {t['docs']:>4} {t['correct']:>5} {t['wrong']:>5} {t['refused']:>5} "
            f"{t['correct_with_issues']:>7} {_fmt(t['recall']):>6} {_fmt(t['precision']):>5} "
            f"{_fmt(t['field_accuracy']):>5}"
        )
    print(f"average {sum(seconds) / len(seconds):.1f}s (median {statistics.median(seconds):.1f}s)")
    print(f"\nWrong values ({len(wrong_lines)}): extracted, but different from the answer key")
    for case_id, field, expected, got in wrong_lines:
        print(f"   {case_id} {field}: expected {expected}  got {got}")
    print(f"\nIssues ({len(issue_lines)}):")
    for case_id, state, field, reason in issue_lines:
        print(f"   {case_id} [{state}] {field}: {reason}")

    out_path = RESULTS_DIR / f"agent2_setb_{_safe(provider.model)}_summary.json"
    out_path.write_text(
        json.dumps(
            {
                "provider": provider.name,
                "model": provider.model,
                "code_hash": fingerprint,
                "ran_now": ran,
                "reused": reused,
                "reused_from_old_code": reused_old,
                "documents": [
                    {"case": c, "kind": k, "status": s, "shape": sh} for c, k, s, sh in rows
                ],
                "summary": summary,
                "wrong_values": wrong_lines,
                "issues": issue_lines,
            },
            indent=2,
        )
    )
    print("\nsaved", out_path)


if __name__ == "__main__":
    main()
