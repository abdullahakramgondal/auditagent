"""Compare models on the same contracts. It reads saved results only: no model is called.

Run:  python -m eval.model_table qwen2.5:7b llama3.1:8b mistral:7b gemma3:4b
      python -m eval.model_table gemini-3.1-flash-lite qwen2.5:7b llama3.1:8b --tier a
It answers: which rule does each model get, which does it refuse, and how many rules are found by
at least one model (a cascade asks the next model only for what the previous one missed).
Only contracts that every listed model has run are compared. A result made by code that is not the
current code is marked, because two models can only be compared fairly on the same code.
"""

import argparse
import json

from auditagent.schemas.extraction import AgentOneResult
from eval.agent1_eval import CODE_FOLDERS, RESULTS_DIR, ROOT, _safe, code_fingerprint
from eval.agent1_scoring import KINDS, score_case

SHORT = {
    "correct": "ok",
    "wrong": "WRONG",
    "refused": "refused",
    "silent_miss": "SILENT",
    "spurious": "SPUR",
    "correct_absent": "-",
}
TIERS = {
    "a": ("agent1", ROOT / "data" / "specs"),
    "b": ("agent1_tierb", ROOT / "data" / "tier_b" / "specs"),
}
COUNTED = ("correct", "wrong", "refused", "silent_miss")


def compare(specs: dict, runs: dict) -> dict:
    """Per rule and per model: the status of the answer.

    specs: {case_id: spec}. runs: {model: {case_id: (AgentOneResult, gold_sources)}}.
    Only contracts that every model has run are counted.
    """
    models = list(runs)
    common = set.intersection(*(set(run) for run in runs.values())) & set(specs)
    rows = []
    for case_id in sorted(common):
        spec = specs[case_id]
        scored = {m: score_case(spec, *runs[m][case_id]) for m in models}
        for kind in KINDS:
            if any(rule["clause_type"] == kind for rule in spec["rules"]):
                status = {m: scored[m][kind]["status"] for m in models}
                rows.append({"case": case_id, "kind": kind, "status": status})

    per_model = {
        m: {name: sum(row["status"][m] == name for row in rows) for name in COUNTED} for m in models
    }
    covered: set = set()
    cumulative = []
    for m in models:
        covered |= {(row["case"], row["kind"]) for row in rows if row["status"][m] == "correct"}
        cumulative.append((m, len(covered)))
    everything = {(row["case"], row["kind"]) for row in rows}
    return {
        "contracts": len(common),
        "rules": len(rows),
        "per_model": per_model,
        "cumulative": cumulative,
        "missed_by_all": sorted(everything - covered),
        "wrong": [
            (row["case"], row["kind"], m)
            for row in rows
            for m in models
            if row["status"][m] == "wrong"
        ],
        "rows": rows,
    }


def load_runs(tag: str, models: list[str]) -> tuple[dict, dict]:
    """The saved results of each model, and a few facts about them (code hash, seconds)."""
    runs, facts = {}, {}
    for model in models:
        folder = RESULTS_DIR / f"{tag}_{_safe(model)}"
        if not folder.is_dir():
            raise SystemExit(f"No saved results for {model}: {folder} is missing")
        saved = {p.stem: json.loads(p.read_text()) for p in sorted(folder.glob("*.json"))}
        runs[model] = {
            case: (AgentOneResult.model_validate(item["result"]), item.get("gold_sources", {}))
            for case, item in saved.items()
        }
        seconds = [item["seconds"] for item in saved.values()]
        facts[model] = {
            "hashes": sorted({item.get("code_hash", "none") for item in saved.values()}),
            "avg_seconds": round(sum(seconds) / len(seconds), 1) if seconds else None,
        }
    return runs, facts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("models", nargs="+", help="model names as in the evals, e.g. qwen2.5:7b")
    parser.add_argument("--tier", choices=sorted(TIERS), default="b")
    args = parser.parse_args()

    tag, spec_dir = TIERS[args.tier]
    specs = {p.stem: json.loads(p.read_text()) for p in sorted(spec_dir.glob("*.json"))}
    runs, facts = load_runs(tag, args.models)
    report = compare(specs, runs)
    current = code_fingerprint(CODE_FOLDERS)

    print(f"tier {args.tier.upper()}   current code {current}")
    for model in args.models:
        info = facts[model]
        old = "" if info["hashes"] == [current] else "   (OLD CODE: not the same code)"
        print(f"  {model}: {info['avg_seconds']} s per contract, code {info['hashes']}{old}")
    print(f"\n{report['contracts']} contracts that every model ran, {report['rules']} rules")

    print(f"\n{'model':26} {'ok':>4} {'wrong':>5} {'refused':>7} {'silent':>6}")
    for model, count in report["per_model"].items():
        print(
            f"{model:26} {count['correct']:>4} {count['wrong']:>5} "
            f"{count['refused']:>7} {count['silent_miss']:>6}"
        )

    print(
        "\nRULES FOUND WHEN THE MODELS ARE ASKED IN THIS ORDER (each adds what the others missed)"
    )
    previous = 0
    for model, total in report["cumulative"]:
        print(f"  + {model:26} {total:>3} of {report['rules']}   (adds {total - previous})")
        previous = total

    print(
        f"\nRULES THAT NO MODEL FOUND ({len(report['missed_by_all'])}): a weakness of the pipeline"
    )
    for case, kind in report["missed_by_all"]:
        print(f"  {case} {kind}")
    if report["wrong"]:
        print("\nWRONG VALUES (look at these first)")
        for case, kind, model in report["wrong"]:
            print(f"  {case} {kind}: {model}")

    print("\nRULES WHERE NOT EVERY MODEL IS RIGHT")
    for row in report["rows"]:
        if not all(status == "correct" for status in row["status"].values()):
            cells = "  ".join(f"{SHORT[row['status'][m]]:>8}" for m in args.models)
            print(f"  {row['case']} {row['kind']:16} {cells}")
    print("  columns: " + ", ".join(args.models))


if __name__ == "__main__":
    main()
