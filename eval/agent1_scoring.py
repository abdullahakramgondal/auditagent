"""Score Agent 1's output against the answer key of a synthetic case.

Pure functions, no LLM and no files: the same scoring can be re-run on saved results.
"""

from decimal import Decimal

from auditagent.ingestion.pdf_parser import normalize_for_match
from auditagent.schemas.extraction import AgentOneResult

KINDS = ("late_penalty", "volume_discount", "payment_terms", "unit_price")
FIELDS = {
    "late_penalty": ("deadline", "mode", "percent", "cap_percent", "grace_days"),
    "volume_discount": ("min_quantity", "discount_percent"),
    "payment_terms": ("net_days",),
    "unit_price": ("item_name", "agreed_unit_price"),
}
TEXT_FIELDS = {"deadline", "mode", "item_name"}
DEFAULTS = {"cap_percent": None, "grace_days": 0}


def _value(rule: dict, field: str):
    return rule.get(field, DEFAULTS.get(field))


def _same(field: str, gold, got) -> bool:
    if gold is None or got is None:
        return gold is None and got is None
    if field in TEXT_FIELDS:
        return str(gold).strip().lower() == str(got).strip().lower()
    return Decimal(str(gold)) == Decimal(str(got))


def score_case(spec: dict, result: AgentOneResult, gold_sources: dict) -> dict:
    """Per clause type: correct, wrong, refused, silent_miss, spurious or correct_absent."""
    scored = {}
    for kind in KINDS:
        gold_rules = [r for r in spec["rules"] if r["clause_type"] == kind]
        got_rules = [
            r.model_dump(mode="json") for r in result.contract.rules if r.clause_type == kind
        ]
        issues = [i for i in result.issues if i.clause_type in (kind, "all")]
        entry = {"gold": len(gold_rules), "found": len(got_rules), "issues": len(issues)}

        if gold_rules and got_rules:
            gold, got = gold_rules[0], got_rules[0]
            fields = {f: _same(f, _value(gold, f), _value(got, f)) for f in FIELDS[kind]}
            source = gold_sources.get(kind)  # Tier B has no gold page or quote: then both stay None
            entry.update(
                status="correct" if all(fields.values()) else "wrong",
                fields=fields,
                page_ok=None if not source else got["source"]["page"] == source.get("page"),
                quote_ok=None
                if not source
                else bool(source.get("text"))
                and normalize_for_match(source["text"])
                in normalize_for_match(got["source"]["text"]),
            )
        elif gold_rules:
            entry["status"] = "refused" if issues else "silent_miss"
        elif got_rules:
            entry["status"] = "spurious"
        else:
            entry["status"] = "correct_absent"
        scored[kind] = entry
    return scored


def _ratio(num: int, den: int):
    return round(num / den, 3) if den else None


def aggregate(scored_cases: list[dict]) -> dict:
    """Totals per clause type and overall: recall, precision, field, page and quote accuracy."""
    keys = (
        "gold",
        "correct",
        "wrong",
        "refused",
        "silent_miss",
        "spurious",
        "correct_absent",
        "pairs",
        "field_ok",
        "field_n",
        "page_ok",
        "page_n",
        "quote_ok",
        "quote_n",
    )
    totals = {kind: dict.fromkeys(keys, 0) for kind in KINDS}
    for case in scored_cases:
        for kind, e in case.items():
            t = totals[kind]
            t["gold"] += e["gold"]
            t[e["status"]] += 1
            if "fields" in e:
                t["pairs"] += 1
                t["field_ok"] += sum(e["fields"].values())
                t["field_n"] += len(e["fields"])
                if e["page_ok"] is not None:
                    t["page_n"] += 1
                    t["page_ok"] += e["page_ok"]
                if e["quote_ok"] is not None:
                    t["quote_n"] += 1
                    t["quote_ok"] += e["quote_ok"]

    totals["ALL"] = {k: sum(totals[kind][k] for kind in KINDS) for k in keys}
    summary = {}
    for name, t in totals.items():
        summary[name] = {
            **t,
            "recall": _ratio(t["correct"], t["gold"]),
            "precision": _ratio(t["correct"], t["correct"] + t["wrong"] + t["spurious"]),
            "field_accuracy": _ratio(t["field_ok"], t["field_n"]),
            "page_accuracy": _ratio(t["page_ok"], t["page_n"]),
            "quote_accuracy": _ratio(t["quote_ok"], t["quote_n"]),
        }
    return summary
