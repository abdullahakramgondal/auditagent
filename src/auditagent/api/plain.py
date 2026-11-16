"""The result of an audit in plain words, for a person who is not a technician.

One place makes these sentences, so the screen and the PDF report always say the same thing.
Nothing is guessed: every sentence is built from the proven rules and the invoice. The only
arithmetic here is counting days.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel

from auditagent.rules.engine import same_item
from auditagent.schemas.audit import ClauseType, Finding
from auditagent.schemas.contract import (
    LatePenaltyRule,
    PaymentTermsRule,
    UnitPriceRule,
    VolumeDiscountRule,
)

if TYPE_CHECKING:
    from auditagent.api.schemas import AuditOut

NOT_KNOWN = "—"
TITLES = {
    "unit_price": "The price per item is higher than agreed",
    "late_penalty": "The delivery was late, but no penalty was taken off",
    "volume_discount": "A discount for a big order was not given",
    "payment_terms": "The payment deadline is shorter than agreed",
}


def pkr(value: Decimal | None) -> str:
    """4462500.00 -> PKR 4,462,500; 1234.5 -> PKR 1,234.50; None -> a dash (not known, never zero)."""
    if value is None:
        return NOT_KNOWN
    sign = "-" if value < 0 else ""
    amount = abs(value)
    text = f"{amount:,.0f}" if amount == amount.to_integral_value() else f"{amount:,.2f}"
    return f"{sign}PKR {text}"


def pct(value: Decimal) -> str:
    """A percentage without a trailing zero: 15.0 -> 15, 2.50 -> 2.5."""
    return format(value.normalize(), "f")


def day(value: date | None) -> str:
    """A date as 9 March 2027."""
    return NOT_KNOWN if value is None else f"{value.day} {value:%B %Y}"


def days(count: int) -> str:
    """1 -> 1 day; 9 -> 9 days."""
    return f"{count} day" if count == 1 else f"{count} days"


def verdict(out: "AuditOut") -> tuple[str, str]:
    """The headline and one line of advice, in plain words."""
    if out.status == "COMPLIANT":
        return "This invoice is correct", "It matches the contract. You can go ahead and pay it."
    if out.status == "NEEDS_REVIEW":
        return (
            "We could not fully check this invoice",
            "Please ask a person to look at it before you pay.",
        )
    if out.total_difference is not None and out.total_difference != 0:
        return (
            "This invoice is too high",
            "Do not pay it as it is. Ask the vendor for a corrected invoice.",
        )
    return (
        "This invoice breaks a rule of the contract",
        "Ask the vendor to correct it before you pay.",
    )


def _rule_for(out: "AuditOut", finding: Finding):
    """The contract rule behind a finding: the one with the same clause text, else the first of its kind."""
    same_kind = [rule for rule in out.contract.rules if rule.clause_type == finding.clause_type]
    exact = next((rule for rule in same_kind if rule.source.text == finding.source.text), None)
    return exact or (same_kind[0] if same_kind else None)


def _penalty_terms(rule: LatePenaltyRule) -> str:
    """The penalty of the contract in plain words."""
    if rule.mode == "flat_percent":
        return f"{pct(rule.percent)}% of the invoice, once"
    text = f"{pct(rule.percent)}% of the invoice for each day of delay"
    if rule.grace_days:
        text += f" (the first {days(rule.grace_days)} are free)"
    if rule.cap_percent:
        text += f", up to a maximum of {pct(rule.cap_percent)}%"
    return text


def _explain_price(out: "AuditOut", rule) -> list[str] | None:
    if not isinstance(rule, UnitPriceRule) or out.invoice is None:
        return None
    row = next((i for i in out.invoice.line_items if same_item(rule.item_name, i.item_name)), None)
    if row is None:
        return None
    return [
        (
            f"The contract says each {rule.item_name} costs {pkr(rule.agreed_unit_price)}. "
            f"The invoice charges {pkr(row.unit_price)} each for {row.quantity} items."
        )
    ]


def _explain_late(out: "AuditOut", rule) -> list[str] | None:
    if not isinstance(rule, LatePenaltyRule) or out.invoice is None:
        return None
    delivered = out.invoice.delivery_date
    if delivered is None:
        return None
    late = (delivered - rule.deadline).days
    return [
        (
            f"The contract says the goods must arrive by {day(rule.deadline)}. "
            f"They arrived on {day(delivered)}, which is {days(late)} late."
        ),
        f"The contract's penalty for this is {_penalty_terms(rule)}.",
        "The invoice does not take the full penalty off, so the vendor is asking for too much.",
    ]


def _explain_volume(out: "AuditOut", rule) -> list[str] | None:
    if not isinstance(rule, VolumeDiscountRule) or out.invoice is None:
        return None
    items = sum(row.quantity for row in out.invoice.line_items)
    return [
        (
            f"The contract gives a {pct(rule.discount_percent)}% discount on orders of "
            f"{rule.min_quantity} or more items. This order has {items} items, so the discount applies."
        ),
        "The invoice does not include the full discount.",
    ]


def _explain_payment(out: "AuditOut", rule) -> list[str] | None:
    invoice = out.invoice
    if not isinstance(rule, PaymentTermsRule) or invoice is None or invoice.due_date is None:
        return None
    given = (invoice.due_date - invoice.invoice_date).days
    earliest = invoice.invoice_date + timedelta(days=rule.net_days)
    return [
        (
            f"The contract gives the buyer {days(rule.net_days)} to pay after the invoice date. "
            f"This invoice is dated {day(invoice.invoice_date)} and asks for payment by "
            f"{day(invoice.due_date)}, which is only {days(given)}."
        ),
        f"The buyer should have until {day(earliest)}.",
    ]


EXPLAINERS = {
    "unit_price": _explain_price,
    "late_penalty": _explain_late,
    "volume_discount": _explain_volume,
    "payment_terms": _explain_payment,
}


def explain(out: "AuditOut", finding: Finding) -> list[str]:
    """What went wrong, in sentences. If a detail is missing, the plain sentence of the engine is used."""
    paragraphs = EXPLAINERS[finding.clause_type](out, _rule_for(out, finding))
    return paragraphs or [finding.description]


def rule_line(rule) -> str:
    """One contract rule that the system used, in plain words."""
    if isinstance(rule, LatePenaltyRule):
        return f"Late delivery after {day(rule.deadline)}: a penalty of {_penalty_terms(rule)}."
    if isinstance(rule, VolumeDiscountRule):
        return f"Orders of {rule.min_quantity} or more items: a {pct(rule.discount_percent)}% discount."
    if isinstance(rule, PaymentTermsRule):
        return f"Payment: {days(rule.net_days)} after the invoice date."
    return f"{rule.item_name}: agreed price {pkr(rule.agreed_unit_price)} per item."


class PlainProblem(BaseModel):
    """One thing that is wrong, written for a person who is not a technician."""

    clause_type: ClauseType
    title: str
    amount_text: str
    paragraphs: list[str]
    page: int
    quote: str


class PlainSummary(BaseModel):
    """The verdict and the problems in plain words: what the screen and the PDF report show."""

    headline: str
    advice: str
    problems: list[PlainProblem]


def problem_of(out: "AuditOut", finding: Finding) -> PlainProblem:
    """One finding as a problem in plain words."""
    amount = (
        f"{pkr(finding.difference)} too much" if finding.difference != 0 else "A rule was broken"
    )
    return PlainProblem(
        clause_type=finding.clause_type,
        title=TITLES[finding.clause_type],
        amount_text=amount,
        paragraphs=explain(out, finding),
        page=finding.source.page,
        quote=finding.source.text,
    )


def plain_summary(out: "AuditOut") -> PlainSummary:
    """The whole result in plain words."""
    headline, advice = verdict(out)
    return PlainSummary(
        headline=headline,
        advice=advice,
        problems=[problem_of(out, finding) for finding in out.findings],
    )
