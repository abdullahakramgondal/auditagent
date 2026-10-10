"""Independent calculator for the expected answer of late-delivery rules."""

from datetime import date
from decimal import Decimal


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