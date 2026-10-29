"""Agent 3 rule engine: the money maths of the audit, in plain Python. No LLM, no guessing.

Input: the rules that Agent 1 proved and the invoice that Agent 2 proved. Output: an AuditResult.
The maths follows docs/scope.md and is written on its own: it never imports or copies
data/generator/ground_truth.py (TODO item 13). The tests compare the two.

  base            = sum of quantity x min(invoice unit price, agreed unit price)
  late penalty    = base x percent (a flat percent applies once, a per-day percent counts the days
                    after the grace period, up to its cap)
  volume discount = base x percent when the units on the invoice reach the minimum
  correct payable = base - discount - penalty
  payment terms   = breached when the invoice due date is earlier than invoice date + Net N days

A deduction that the vendor already applied is read from the invoice adjustments (TODO item 15),
never from the spec. Anything that cannot be checked becomes a review reason, never silence.
One rule per type is the v1 case (the generated dataset has no more).
"""

import re
from collections.abc import Iterable
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from auditagent.schemas.audit import AuditResult, Finding
from auditagent.schemas.contract import (
    ExtractedContract,
    LatePenaltyRule,
    PaymentTermsRule,
    Source,
    UnitPriceRule,
    VolumeDiscountRule,
)
from auditagent.schemas.invoice import InvoiceData

CENT = Decimal("0.01")
ZERO = Decimal(0)
HUNDRED = Decimal(100)

# An adjustment with a negative amount is a deduction. The words of its label say which rule it applies.
_LATE_WORDS = re.compile(r"\b(?:late|penalt\w*|delay\w*|liquidated)\b", re.IGNORECASE)
_VOLUME_WORDS = re.compile(r"\b(?:volume|quantity|bulk|discount|rebate|reduction)\b", re.IGNORECASE)


def money(value: Decimal) -> Decimal:
    """Round to two decimals, half up."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _pkr(value: Decimal) -> str:
    return f"PKR {money(value):,.2f}"


def _day(value: date) -> str:
    return f"{value.day} {value:%B %Y}"


def _key(text: str) -> str:
    return " ".join(text.split()).lower()


def same_item(first: str, second: str) -> bool:
    """True if one item name is written inside the other ("Leased Line 100 Mbps" and "... (annual)").

    Items are matched by normalised containment, never by equality (TODO item 56).
    """
    a, b = _key(first), _key(second)
    return bool(a) and bool(b) and (a in b or b in a)


def late_penalty_percent(rule: LatePenaltyRule, delivered: date) -> Decimal:
    """The percentage of the base that the vendor owes for this delivery date."""
    days_late = max(0, (delivered - rule.deadline).days)
    if rule.mode == "flat_percent":
        return rule.percent if days_late > rule.grace_days else ZERO
    percent = rule.percent * max(0, days_late - rule.grace_days)
    if rule.cap_percent is not None:
        percent = min(percent, rule.cap_percent)
    return min(percent, HUNDRED)


def applied_deductions(invoice: InvoiceData) -> tuple[dict[str, Decimal], list[str]]:
    """What the vendor already deducted per rule, read from the invoice adjustments.

    Returns the amounts per clause type and the labels of the adjustments that no rule explains.
    """
    applied = {"late_penalty": ZERO, "volume_discount": ZERO}
    unmatched = []
    for adjustment in invoice.adjustments:
        if adjustment.amount < 0 and _LATE_WORDS.search(adjustment.label):
            applied["late_penalty"] += -adjustment.amount
        elif adjustment.amount < 0 and _VOLUME_WORDS.search(adjustment.label):
            applied["volume_discount"] += -adjustment.amount
        else:
            unmatched.append(adjustment.label)
    return applied, unmatched


def _base_and_price_findings(agreed: list[UnitPriceRule], invoice: InvoiceData):
    """The base total at the right prices, and one finding per agreed price that the invoice exceeds."""
    base = ZERO
    billed: dict[int, Decimal] = {}
    right: dict[int, Decimal] = {}
    for item in invoice.line_items:
        index = next(
            (i for i, rule in enumerate(agreed) if same_item(rule.item_name, item.item_name)), None
        )
        price = item.unit_price
        if index is not None and price > agreed[index].agreed_unit_price:
            price = agreed[index].agreed_unit_price
            billed[index] = billed.get(index, ZERO) + item.quantity * item.unit_price
            right[index] = right.get(index, ZERO) + item.quantity * price
        base += item.quantity * price

    findings = []
    for index, billed_amount in billed.items():
        rule = agreed[index]
        difference = billed_amount - right[index]
        findings.append(
            Finding(
                clause_type="unit_price",
                description=(
                    f"{rule.item_name} is billed above the agreed unit price of "
                    f"{_pkr(rule.agreed_unit_price)}: {_pkr(difference)} overbilled."
                ),
                source=rule.source,
                expected_amount=money(right[index]),
                billed_amount=money(billed_amount),
                difference=money(difference),
            )
        )
    return base, findings


def _deduction_finding(
    kind: str,
    source: Source,
    description: str,
    base: Decimal,
    owed: Decimal,
    applied: Decimal,
) -> Finding | None:
    """A finding for a penalty or discount that was owed and not (fully) deducted by the vendor."""
    difference = owed - applied
    if difference <= 0:
        return None
    billed = base - applied
    return Finding(
        clause_type=kind,
        description=description,
        source=source,
        expected_amount=money(max(billed - difference, ZERO)),
        billed_amount=money(billed),
        difference=money(difference),
    )


def audit_invoice(
    contract: ExtractedContract,
    invoice: InvoiceData,
    extra_review_reasons: Iterable[str] = (),
) -> AuditResult:
    """Audit one invoice against the proven rules of its contract.

    extra_review_reasons carries the issues of Agent 1 and Agent 2 (TODO item 28).
    """
    reasons = list(extra_review_reasons)
    rules = contract.rules
    applied, unmatched = applied_deductions(invoice)
    base, findings = _base_and_price_findings(
        [rule for rule in rules if isinstance(rule, UnitPriceRule)], invoice
    )
    units = sum(item.quantity for item in invoice.line_items)
    deductions = ZERO

    for rule in rules:
        if isinstance(rule, VolumeDiscountRule) and units >= rule.min_quantity:
            owed = base * rule.discount_percent / HUNDRED
            deductions += owed
            finding = _deduction_finding(
                "volume_discount",
                rule.source,
                f"The invoice has {units} units, the contract gives {rule.discount_percent}% "
                f"from {rule.min_quantity} units: {_pkr(owed)} discount not applied.",
                base,
                owed,
                applied["volume_discount"],
            )
            findings += [finding] if finding else []
        elif isinstance(rule, LatePenaltyRule):
            if invoice.delivery_date is None:
                reasons.append(
                    "The invoice shows no delivery date, so the late delivery penalty "
                    "cannot be checked."
                )
                continue
            percent = late_penalty_percent(rule, invoice.delivery_date)
            owed = base * percent / HUNDRED
            deductions += owed
            days_late = max(0, (invoice.delivery_date - rule.deadline).days)
            finding = _deduction_finding(
                "late_penalty",
                rule.source,
                f"Delivered on {_day(invoice.delivery_date)}, {days_late} days after "
                f"{_day(rule.deadline)}: a penalty of {percent}% ({_pkr(owed)}) applies "
                "and was not deducted.",
                base,
                owed,
                applied["late_penalty"],
            )
            findings += [finding] if finding else []
        elif isinstance(rule, PaymentTermsRule):
            if invoice.due_date is None:
                reasons.append(
                    "The invoice shows no due date, so the payment terms cannot be checked."
                )
                continue
            earliest = invoice.invoice_date + timedelta(days=rule.net_days)
            if invoice.due_date < earliest:
                findings.append(
                    Finding(
                        clause_type="payment_terms",
                        description=(
                            f"The invoice is due on {_day(invoice.due_date)}, earlier than "
                            f"{_day(earliest)} (Net {rule.net_days} days from the invoice date)."
                        ),
                        source=rule.source,
                    )
                )

    correct = max(base - deductions, ZERO)
    total_difference = sum((finding.difference for finding in findings), ZERO)
    if money(invoice.total_amount - correct) != money(total_difference):
        reasons.append(
            f"The billed total {_pkr(invoice.total_amount)} minus the correct payable "
            f"{_pkr(correct)} is not the sum of the findings ({_pkr(total_difference)}): "
            "the invoice has amounts that no rule explains."
        )
    reasons += [
        f"The invoice adjustment {label!r} matches no contract rule: check it."
        for label in unmatched
    ]

    if findings:
        status = "NON_COMPLIANT"
    elif reasons:
        status = "NEEDS_REVIEW"
    else:
        status = "COMPLIANT"
    return AuditResult(
        status=status,
        billed_total=money(invoice.total_amount),
        correct_payable=money(correct),
        total_difference=money(total_difference),
        findings=findings,
        review_reasons=reasons,
    )
