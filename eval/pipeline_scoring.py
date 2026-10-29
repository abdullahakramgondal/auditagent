"""Score the whole pipeline against the answer key of a synthetic case.

Pure functions, no LLM and no files: the same scoring can be re-run on saved results.

Outcomes of one case:
  correct  the status, the three amounts and the finding types all equal the answer key
  review   the pipeline said NEEDS_REVIEW where the key has a verdict: safe, a human looks at it
  wrong    anything else: a verdict that differs from the key (the number that must stay at 0)
A correct case that still carries review reasons is counted in correct_with_reasons (a false alarm).
"""

from decimal import Decimal

from auditagent.schemas.audit import AuditResult

AMOUNTS = ("billed_total", "correct_payable", "total_difference")


def _same_amount(got, want) -> bool:
    return got is not None and Decimal(str(got)) == Decimal(str(want))


def score_case(expected: dict, result: AuditResult) -> dict:
    """One case: which checks passed, and the outcome."""
    checks = {"status": result.status == expected["status"]}
    for name in AMOUNTS:
        if name in expected:
            checks[name] = _same_amount(getattr(result, name), expected[name])
    checks["finding_types"] = sorted(f.clause_type for f in result.findings) == sorted(
        expected["finding_types"]
    )
    if all(checks.values()):
        outcome = "correct"
    elif result.status == "NEEDS_REVIEW":
        outcome = "review"
    else:
        outcome = "wrong"
    return {
        "outcome": outcome,
        "checks": checks,
        "status": result.status,
        "expected_status": expected["status"],
        "reasons": len(result.review_reasons),
    }


def _ratio(num: int, den: int):
    return round(num / den, 3) if den else None


def aggregate(scored: list[dict]) -> dict:
    """Totals per category and overall. Every scored case carries its "category"."""
    keys = ("cases", "correct", "review", "wrong", "correct_with_reasons")
    totals: dict[str, dict] = {}
    for entry in scored:
        for name in (entry["category"], "ALL"):
            t = totals.setdefault(name, dict.fromkeys(keys, 0))
            t["cases"] += 1
            t[entry["outcome"]] += 1
            if entry["outcome"] == "correct" and entry["reasons"] > 0:
                t["correct_with_reasons"] += 1
    return {name: {**t, "accuracy": _ratio(t["correct"], t["cases"])} for name, t in totals.items()}
