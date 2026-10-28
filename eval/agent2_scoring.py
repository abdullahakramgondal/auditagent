"""Score Agent 2's output against the answer key of a synthetic case.

Pure functions, no LLM and no files: the same scoring can be re-run on saved results.
"""

from pydantic import BaseModel

from auditagent.schemas.extraction import ExtractionIssue
from auditagent.schemas.invoice import InvoiceData, PurchaseOrderData

KINDS = ("invoice", "purchase_order")
MODELS = {"invoice": InvoiceData, "purchase_order": PurchaseOrderData}
FIELDS = {
    "invoice": (
        "invoice_number",
        "invoice_date",
        "delivery_date",
        "due_date",
        "line_items",
        "adjustments",
        "total_amount",
    ),
    "purchase_order": (
        "po_number",
        "po_date",
        "delivery_due_date",
        "line_items",
        "total_amount",
    ),
}


def differences(kind: str, gold: dict, data: BaseModel) -> dict[str, tuple[str, str]]:
    """The fields where the extracted document differs from the answer key: {field: (expected, got)}."""
    expected = MODELS[kind].model_validate(gold)
    return {
        name: (str(getattr(expected, name)), str(getattr(data, name)))
        for name in FIELDS[kind]
        if getattr(data, name) != getattr(expected, name)
    }


def score_document(
    kind: str, gold: dict, data: BaseModel | None, issues: list[ExtractionIssue]
) -> dict:
    """One document: correct, wrong (extracted but different from the key) or refused (not extracted).

    Money is compared as Decimal, so 40000.0 equals 40000.
    """
    entry = {"issues": len(issues)}
    if data is None:
        entry["status"] = "refused"
        return entry
    diff = differences(kind, gold, data)
    entry["status"] = "wrong" if diff else "correct"
    entry["fields"] = {name: name not in diff for name in FIELDS[kind]}
    entry["differences"] = diff
    return entry


def _ratio(num: int, den: int):
    return round(num / den, 3) if den else None


def aggregate(scored_cases: list[dict]) -> dict:
    """Totals per kind of document and overall: recall, precision and field accuracy.

    recall = correct / all documents; precision = correct / extracted documents (correct + wrong).
    correct_with_issues counts documents that are right but still carry an issue (for example a
    printed arithmetic problem, or a false alarm).
    """
    keys = (
        "docs",
        "correct",
        "wrong",
        "refused",
        "correct_with_issues",
        "field_ok",
        "field_n",
    )
    totals = {kind: dict.fromkeys(keys, 0) for kind in KINDS}
    for case in scored_cases:
        for kind, entry in case.items():
            t = totals[kind]
            t["docs"] += 1
            t[entry["status"]] += 1
            if entry["status"] == "correct" and entry["issues"] > 0:
                t["correct_with_issues"] += 1
            if "fields" in entry:
                t["field_ok"] += sum(entry["fields"].values())
                t["field_n"] += len(entry["fields"])
    totals["ALL"] = {k: sum(totals[kind][k] for kind in KINDS) for k in keys}
    return {
        name: {
            **t,
            "recall": _ratio(t["correct"], t["docs"]),
            "precision": _ratio(t["correct"], t["correct"] + t["wrong"]),
            "field_accuracy": _ratio(t["field_ok"], t["field_n"]),
        }
        for name, t in totals.items()
    }
