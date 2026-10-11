"""Independent calculator for the expected answer of a synthetic case."""

from datetime import date, timedelta
from decimal import Decimal

CENT = Decimal("0.01")


def _money(x) -> Decimal:
    return Decimal(x).quantize(CENT)


def days_late(deadline: date, delivered: date) -> int:
    return max(0, (delivered - deadline).days)


def late_penalty_percent(rule: dict, delivered: date) -> Decimal:
    late = days_late(date.fromisoformat(rule["deadline"]), delivered)
    grace = int(rule.get("grace_days", 0))
    percent = Decimal(str(rule["percent"]))

    if rule["mode"] == "flat_percent":
        return percent if late > grace else Decimal("0")

    counted = max(0, late - grace)
    pct = percent * counted
    cap = rule.get("cap_percent")
    if cap is not None:
        pct = min(pct, Decimal(str(cap)))
    return min(pct, Decimal("100"))


def expected_late_penalty(rule: dict, invoice_total, delivered: date) -> Decimal:
    return Decimal(str(invoice_total)) * late_penalty_percent(rule, delivered) / Decimal(100)


def evaluate_case(spec: dict) -> dict:
    """Expected audit outcome, computed only from the rules and the invoice facts.

    `spec["vendor_applied"]` (answer key only, not visible in the PDFs) lists the
    deductions the vendor already applied, so they are not reported as findings.
    """
    rules = spec["rules"]
    inv = spec["invoice"]
    applied = set(spec.get("vendor_applied", []))

    by_type: dict[str, list[dict]] = {}
    for r in rules:
        by_type.setdefault(r["clause_type"], []).append(r)
    agreed = {
        r["item_name"]: Decimal(str(r["agreed_unit_price"])) for r in by_type.get("unit_price", [])
    }

    base = Decimal(0)
    overcharge = Decimal(0)
    total_qty = 0
    for item in inv["line_items"]:
        paid = Decimal(str(item["unit_price"]))
        qty = item["quantity"]
        total_qty += qty
        cap = agreed.get(item["item_name"])
        right_price = min(paid, cap) if cap is not None else paid
        base += qty * right_price
        overcharge += qty * (paid - right_price)

    penalty = Decimal(0)
    for r in by_type.get("late_penalty", []):
        if not inv.get("delivery_date"):
            raise ValueError("late_penalty rule needs invoice delivery_date")
        delivered = date.fromisoformat(inv["delivery_date"])
        penalty += base * late_penalty_percent(r, delivered) / 100

    discount = Decimal(0)
    for r in by_type.get("volume_discount", []):
        if total_qty >= r["min_quantity"]:
            discount += base * Decimal(str(r["discount_percent"])) / 100

    terms_breach = False
    for r in by_type.get("payment_terms", []):
        if inv.get("due_date"):
            allowed = date.fromisoformat(inv["invoice_date"]) + timedelta(days=r["net_days"])
            terms_breach = terms_breach or date.fromisoformat(inv["due_date"]) < allowed

    findings: dict[str, Decimal] = {}
    if overcharge > 0:
        findings["unit_price"] = overcharge
    if discount > 0 and "volume_discount" not in applied:
        findings["volume_discount"] = discount
    if penalty > 0 and "late_penalty" not in applied:
        findings["late_penalty"] = penalty
    if terms_breach:
        findings["payment_terms"] = Decimal(0)

    return {
        "status": "NON_COMPLIANT" if findings else "COMPLIANT",
        "billed_total": _money(Decimal(str(inv["total_amount"]))),
        "correct_payable": _money(base - discount - penalty),
        "total_difference": _money(sum(findings.values(), Decimal(0))),
        "finding_types": sorted(findings),
        "finding_amounts": {k: _money(v) for k, v in findings.items()},
    }