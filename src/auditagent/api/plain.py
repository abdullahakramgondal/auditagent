"""The result of an audit in plain words, for a person who is not a technician.

One place makes these sentences, so the screen and the PDF report always say the same thing.
Nothing is guessed: every sentence is built from the proven rules and the invoice. The only
arithmetic here is counting days and the working-out lines (the same numbers as the rule engine).
"""

import re
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from auditagent.rules.engine import applied_deductions, late_penalty_percent, money, same_item
from auditagent.schemas.audit import ClauseType, Finding
from auditagent.schemas.contract import (
    LatePenaltyRule,
    PaymentTermsRule,
    UnitPriceRule,
    VolumeDiscountRule,
)
from auditagent.schemas.invoice import InvoiceData

if TYPE_CHECKING:
    from auditagent.api.schemas import AuditOut, ReviewReason

NOT_KNOWN = "—"
TITLES = {
    "unit_price": "The price per item is higher than agreed",
    "late_penalty": "The delivery was late, but no penalty was taken off",
    "volume_discount": "A discount for a big order was not given",
    "payment_terms": "The payment deadline is shorter than agreed",
}
MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


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
        count = len(out.contract.rules)
        if count == 0:
            found = "No rule was found in the contract to check."
        elif count == 1:
            found = "The 1 rule we found in the contract matches the invoice."
        else:
            found = f"All {count} rules we found in the contract match the invoice."
        return "No problems found", f"{found} Tax and extra charges are not checked."
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


def _explain_price(out: "AuditOut", rule, finding: Finding) -> list[str] | None:
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


def _not_taken_off(out: "AuditOut", kind: str, finding: Finding, what: str) -> str:
    """The closing sentence of a missed penalty or discount: nothing taken off, or only a part."""
    taken = applied_deductions(out.invoice)[0][kind] if out.invoice else Decimal(0)
    if taken == 0:
        return f"The invoice does not show this {what}."
    owed = taken + finding.difference
    return f"The invoice takes off only {pkr(taken)} of the {pkr(owed)} that is owed."


def _explain_late(out: "AuditOut", rule, finding: Finding) -> list[str] | None:
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
        _not_taken_off(out, "late_penalty", finding, "penalty being taken off")
        + " So the vendor is asking for too much.",
    ]


def _explain_volume(out: "AuditOut", rule, finding: Finding) -> list[str] | None:
    if not isinstance(rule, VolumeDiscountRule) or out.invoice is None:
        return None
    items = sum(row.quantity for row in out.invoice.line_items)
    return [
        (
            f"The contract gives a {pct(rule.discount_percent)}% discount on orders of "
            f"{rule.min_quantity} or more items. This order has {items} items, so the discount applies."
        ),
        _not_taken_off(out, "volume_discount", finding, "discount"),
    ]


def _explain_payment(out: "AuditOut", rule, finding: Finding) -> list[str] | None:
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
        "This one does not change the amount to pay.",
    ]


EXPLAINERS = {
    "unit_price": _explain_price,
    "late_penalty": _explain_late,
    "volume_discount": _explain_volume,
    "payment_terms": _explain_payment,
}


def explain(out: "AuditOut", finding: Finding) -> list[str]:
    """What went wrong, in sentences. If a detail is missing, the plain sentence of the engine is used."""
    paragraphs = EXPLAINERS[finding.clause_type](out, _rule_for(out, finding), finding)
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


# ---- the working-out: the sums behind the verdict ----


class CalcStep(BaseModel):
    """One line of the working-out: what is added or taken off, and why."""

    kind: Literal["start", "base", "minus", "result", "difference"]
    label: str
    detail: str
    amount_text: str


def _asking_detail(inv: InvoiceData, asked: list[str]) -> str:
    """How the invoice total is made: the rows, then what the vendor already took off or added."""
    detail = " + ".join(asked)
    if not inv.adjustments:
        return detail
    rows_total = sum((i.quantity * i.unit_price for i in inv.line_items), Decimal(0))
    detail += f" = {pkr(rows_total)}"
    for adjustment in inv.adjustments:
        if adjustment.amount < 0:
            detail += (
                f" − {pkr(-adjustment.amount)} "
                f"(already taken off by the vendor: {adjustment.label})"
            )
        else:
            detail += f" + {pkr(adjustment.amount)} ({adjustment.label})"
    return detail


def calculation(out: "AuditOut") -> list[CalcStep]:
    """The sums behind the verdict, line by line. Empty when no amounts could be proven."""
    inv = out.invoice
    if inv is None or out.status == "NEEDS_REVIEW":
        return []
    if out.billed_total is None or out.correct_payable is None:
        return []

    agreed = [r for r in out.contract.rules if isinstance(r, UnitPriceRule)]
    base, asked, right = Decimal(0), [], []
    for item in inv.line_items:
        rule = next((r for r in agreed if same_item(r.item_name, item.item_name)), None)
        price = min(item.unit_price, rule.agreed_unit_price) if rule else item.unit_price
        base += item.quantity * price
        asked.append(f"{item.quantity} × {pkr(item.unit_price)}")
        right.append(f"{item.quantity} × {pkr(price)}")

    steps = [
        CalcStep(
            kind="start",
            label="What the vendor is asking for",
            detail=_asking_detail(inv, asked),
            amount_text=pkr(out.billed_total),
        ),
        CalcStep(
            kind="base",
            label=(
                "The same goods at the agreed price" if agreed else "The goods at the invoice price"
            ),
            detail=" + ".join(right) + (" (the price in the contract)" if agreed else ""),
            amount_text=pkr(base),
        ),
    ]

    units = sum(item.quantity for item in inv.line_items)
    taken: list[str] = []
    for rule in out.contract.rules:
        if isinstance(rule, LatePenaltyRule) and inv.delivery_date is not None:
            percent = late_penalty_percent(rule, inv.delivery_date)
            if percent <= 0:
                continue
            late_days = (inv.delivery_date - rule.deadline).days
            how = f"{days(late_days)} late"
            if rule.grace_days:
                how += f", the first {days(rule.grace_days)} are free"
            if rule.mode == "per_day_percent":
                counted = max(0, late_days - rule.grace_days)
                how += f", so {counted} × {pct(rule.percent)}% = {pct(percent)}%"
                if rule.cap_percent is not None and percent == rule.cap_percent:
                    how += " (the maximum)"
            else:
                how += f", so a flat {pct(percent)}%"
            amount = money(base * percent / 100)
            taken.append(pkr(amount))
            steps.append(
                CalcStep(
                    kind="minus",
                    label="Late delivery penalty",
                    detail=f"{how}, of {pkr(base)}",
                    amount_text=f"− {pkr(amount)}",
                )
            )
        elif isinstance(rule, VolumeDiscountRule) and units >= rule.min_quantity:
            amount = money(base * rule.discount_percent / 100)
            taken.append(pkr(amount))
            steps.append(
                CalcStep(
                    kind="minus",
                    label="Volume discount",
                    detail=(
                        f"{pct(rule.discount_percent)}% of {pkr(base)}, because the order has "
                        f"{units} items (the discount starts at {rule.min_quantity})"
                    ),
                    amount_text=f"− {pkr(amount)}",
                )
            )

    steps.append(
        CalcStep(
            kind="result",
            label="The right amount to pay",
            detail=" − ".join([pkr(base), *taken]),
            amount_text=pkr(out.correct_payable),
        )
    )
    if out.total_difference:
        steps.append(
            CalcStep(
                kind="difference",
                label="Overcharged by",
                detail=f"{pkr(out.billed_total)} − {pkr(out.correct_payable)}",
                amount_text=pkr(out.total_difference),
            )
        )
    return steps


# ---- what was checked: one line for each of the four things ----


class CheckItem(BaseModel):
    """One of the four things the system checks, and how it went."""

    clause_type: ClauseType
    label: str
    state: Literal["ok", "problem", "unchecked", "none"]
    detail: str


CHECK_ORDER = ("unit_price", "volume_discount", "late_penalty", "payment_terms")
CHECK_LABELS = {
    "unit_price": "Price per item",
    "volume_discount": "Volume discount",
    "late_penalty": "Delivery on time",
    "payment_terms": "Payment deadline",
}


def _check_ok(rule, inv: InvoiceData) -> tuple[str, str]:
    """The state and the sentence of a rule that has no finding."""
    if isinstance(rule, UnitPriceRule):
        row = next((i for i in inv.line_items if same_item(rule.item_name, i.item_name)), None)
        if row is None:
            return "unchecked", f"No item on the invoice is called {rule.item_name}."
        return (
            "ok",
            (
                f"The invoice charges {pkr(row.unit_price)} per item, "
                f"not above the agreed {pkr(rule.agreed_unit_price)}."
            ),
        )
    if isinstance(rule, VolumeDiscountRule):
        units = sum(item.quantity for item in inv.line_items)
        if units >= rule.min_quantity:
            return "ok", f"The order has {units} items and the discount was taken."
        return (
            "ok",
            f"The order has {units} items, below {rule.min_quantity}, so no discount is owed.",
        )
    if isinstance(rule, LatePenaltyRule):
        if inv.delivery_date is None:
            return "unchecked", "The invoice shows no delivery date."
        late_days = (inv.delivery_date - rule.deadline).days
        if late_penalty_percent(rule, inv.delivery_date) > 0:
            return "ok", "A penalty was owed and the vendor already took it off."
        if late_days <= 0:
            return "ok", f"Delivered on time ({day(inv.delivery_date)})."
        return "ok", f"Delivered {days(late_days)} late, but inside the free days."
    if isinstance(rule, PaymentTermsRule):
        if inv.due_date is None:
            return "unchecked", "The invoice shows no payment due date."
        return (
            "ok",
            (
                f"The invoice is due on {day(inv.due_date)}, "
                f"at least {days(rule.net_days)} after the invoice date."
            ),
        )
    return "unchecked", "This rule could not be checked."


def _check_problem(out: "AuditOut", rule, finding: Finding) -> str:
    """The real detail of a check that found a problem."""
    fallback = "A problem was found: see above."
    inv = out.invoice
    if inv is None or rule is None:
        return fallback
    if isinstance(rule, UnitPriceRule):
        row = next((i for i in inv.line_items if same_item(rule.item_name, i.item_name)), None)
        if row is not None:
            return (
                f"The invoice charges {pkr(row.unit_price)} per item, "
                f"above the agreed {pkr(rule.agreed_unit_price)}."
            )
    elif isinstance(rule, VolumeDiscountRule):
        taken = applied_deductions(inv)[0]["volume_discount"]
        if taken == 0:
            return (
                f"No discount on the invoice, {pct(rule.discount_percent)}% "
                f"({pkr(finding.difference)}) was due."
            )
        return (
            f"The invoice takes off only {pkr(taken)}, {pkr(finding.difference)} is still missing."
        )
    elif isinstance(rule, LatePenaltyRule):
        if inv.delivery_date is None:
            return fallback
        late_days = (inv.delivery_date - rule.deadline).days
        taken = applied_deductions(inv)[0]["late_penalty"]
        if taken == 0:
            return (
                f"Delivered {days(late_days)} late, a penalty of {pkr(finding.difference)} "
                "was due and the invoice does not show it."
            )
        return (
            f"Delivered {days(late_days)} late, the invoice takes off only {pkr(taken)}, "
            f"{pkr(finding.difference)} is still missing."
        )
    elif isinstance(rule, PaymentTermsRule):
        if inv.due_date is None:
            return fallback
        given = (inv.due_date - inv.invoice_date).days
        return f"Payment is due in {days(given)}, the contract gives {days(rule.net_days)}."
    return fallback


def checks(out: "AuditOut") -> list[CheckItem]:
    """The four checks, each with its state. 'none' means that the contract has no such rule."""
    inv = out.invoice
    found = {finding.clause_type: finding for finding in out.findings}
    refused = {reason.field for reason in out.review_reasons if reason.source == "contract"}
    items = []
    for kind in CHECK_ORDER:
        rule = next((r for r in out.contract.rules if r.clause_type == kind), None)
        if kind in found:
            state = "problem"
            detail = _check_problem(out, _rule_for(out, found[kind]), found[kind])
        elif rule is None and (kind in refused or "all" in refused):
            state, detail = "unchecked", "We could not read this rule in the contract."
        elif rule is None:
            state, detail = "none", "We found no rule about this in the contract."
        elif inv is None:
            state, detail = "unchecked", "The invoice could not be read."
        else:
            state, detail = _check_ok(rule, inv)
        items.append(
            CheckItem(clause_type=kind, label=CHECK_LABELS[kind], state=state, detail=detail)
        )
    return items


# ---- the review reasons in plain words ----


class ReviewNote(BaseModel):
    """One thing the system could not prove: what happened, what to do, and the technical text."""

    group: str
    title: str
    what: str
    todo: str
    technical: str


GROUPS = {
    "contract": "About the contract",
    "invoice": "About the invoice",
    "purchase_order": "About the purchase order",
    "audit": "General",
}
FIELD_WORDS = {
    "invoice_number": "invoice number",
    "invoice_date": "invoice date",
    "delivery_date": "delivery date",
    "due_date": "payment due date",
    "line_items": "list of items",
    "adjustments": "discount or extra charge lines",
    "total_amount": "total",
    "line_total": "amount of an item",
    "po_number": "order number",
    "po_date": "order date",
    "delivery_due_date": "required delivery date",
}
DATE_PHRASES = {
    "invoice_date": "is dated",
    "delivery_date": "says it was delivered on",
    "due_date": "asks for payment by",
    "po_date": "is dated",
    "delivery_due_date": "asks for delivery by",
}
CLAUSE_WORDS = {
    "late_penalty": "late-delivery penalty",
    "volume_discount": "volume discount",
    "payment_terms": "payment terms",
    "unit_price": "agreed price",
}
_QUOTED_ISO = re.compile(r"'(\d{4})-(\d{2})-(\d{2})'")


def _sentence(text: str) -> str:
    text = text.strip()
    return text if text.endswith((".", "!", "?")) else text + "."


def _written_date(text: str) -> str | None:
    """'2027-02-31' inside a message -> 31 February 2027 (the date is not checked, only written out)."""
    match = _QUOTED_ISO.search(text)
    if match is None:
        return None
    year, month, number = (int(group) for group in match.groups())
    if not 1 <= month <= 12:
        return None
    return f"{number} {MONTHS[month - 1]} {year}"


def _contract_note(field: str, text: str) -> tuple[str, str, str]:
    low = text.lower()
    clause = CLAUSE_WORDS.get(field, "rule")
    by_hand = f"Read the {clause} part of the contract and check the invoice by hand."
    if field == "all":
        return (
            "The contract could not be read",
            "The contract has no text that the system can read. It may be a scan or a picture.",
            "Upload a text PDF of the contract, or check it by hand.",
        )
    if "keywords found" in low:
        return (
            f"The {clause} may be in the contract, but we could not read it",
            (
                "The contract seems to talk about this, but the system could not read the rule "
                "with certainty. It did not guess."
            ),
            by_hand,
        )
    if "different" in low and "rules" in low:
        return (
            f"The contract seems to give two different {clause} rules",
            "The system found more than one rule for the same thing and cannot tell which one counts.",
            "Ask a person which one applies.",
        )
    if "output unusable" in low:
        return (
            "The system could not read this part of the contract",
            "The language model gave an answer that could not be used.",
            "Try the audit again in a few minutes.",
        )
    if "deadline" in low:
        return (
            "The delivery date of the contract could not be found",
            (
                "We could not find the date that the late-delivery penalty counts from, "
                "so the penalty was not checked."
            ),
            "Look for the delivery date in the contract and check late delivery by hand.",
        )
    if "quote not found" in low:
        return (
            f"We could not find the exact words of the {clause} in the contract",
            "The system proposed a rule, but its words are not in the contract, so it was not used.",
            by_hand,
        )
    return (
        f"The {clause} could not be proven",
        (
            "The system could not confirm this rule from the exact words of the contract, "
            "so it did not use it."
        ),
        by_hand,
    )


def _document_note(noun: str, field: str, text: str) -> tuple[str, str, str]:
    low = text.lower()
    word = FIELD_WORDS.get(field, field.replace("_", " ") or "value")
    by_hand = f"Open the {noun} PDF and check it by hand."
    if field == "document":
        return (
            f"The {noun} could not be read",
            f"The {noun} has no text that the system can read. It may be a scan or a picture.",
            f"Upload a text PDF of the {noun}, or check it by hand.",
        )
    if "returned none" in low:
        return (
            f"We could not read the {word}",
            f"The {noun} seems to show a {word}, but the system could not read it with certainty.",
            by_hand,
        )
    if "not a valid" in low:
        shown = _written_date(text)
        phrase = DATE_PHRASES.get(field)
        if shown and phrase:
            what = f"The {noun} {phrase} {shown}, but that date does not exist."
        elif shown:
            what = f"The {noun} shows {shown} as the {word}, but that date does not exist."
        else:
            what = f"The {word} on the {noun} is not a date that exists."
        return (
            f"The {word} on the {noun} is not a real date",
            what,
            f"Check the {noun} PDF. If the date is wrong, ask for a corrected {noun}.",
        )
    if "labelled" in low:
        return (
            f"We could not match the {word} to its label",
            "The system found a date but could not be sure which date it stands for.",
            by_hand,
        )
    if "add up" in low or "but the document shows" in low:
        return (
            f"The numbers on the {noun} do not add up",
            _sentence(text),
            f"Ask for a corrected {noun}.",
        )
    if field == "line_items":
        return (
            f"We could not confirm an item on the {noun}",
            "The system could not match one of the item rows with its name, quantity and price.",
            by_hand,
        )
    return (
        f"The {word} on the {noun} could not be confirmed",
        f"The system could not prove this value from the text of the {noun}, so it did not use it.",
        by_hand,
    )


def _audit_note(text: str) -> tuple[str, str, str]:
    low = text.lower()
    quoted = re.search(r"'([^']+)'", text)
    name = quoted.group(1) if quoted else "this item"
    if "invoice could not be proven" in low:
        return (
            "The invoice could not be read with certainty",
            "Because of the problems above, no amount was checked.",
            "Open the invoice PDF and check it by hand, or upload a clearer copy.",
        )
    if "purchase order could not be proven" in low:
        return (
            "The purchase order could not be read with certainty",
            "The purchase order was not compared with the invoice.",
            "Check the order by hand.",
        )
    if "no audit rule was found" in low:
        return (
            "No rule could be read from the contract",
            "Nothing could be checked, because the system found none of the four rules.",
            "Check the contract by hand.",
        )
    if "shows no delivery date" in low:
        return (
            "The invoice shows no delivery date",
            "Without it we cannot tell if the delivery was late, so the penalty was not checked.",
            "Ask the vendor for the delivery date.",
        )
    if "shows no due date" in low:
        return (
            "The invoice shows no payment due date",
            "Without it we cannot check the payment deadline.",
            "Ask the vendor for the due date.",
        )
    if "fixes a unit price" in low:
        return (
            "An agreed price could not be matched to the invoice",
            f"The contract fixes a price for {name}, but no item on the invoice has that name.",
            "Compare the item names in the contract and on the invoice.",
        )
    if "not the sum of the findings" in low:
        return (
            "Part of the invoice is not explained by the contract",
            (
                "The invoice has amounts that none of the contract rules explain, "
                "so the totals may be incomplete."
            ),
            "Ask the vendor what the extra amounts are for.",
        )
    if "matches no contract rule" in low:
        return (
            "An extra line on the invoice is not in the contract",
            f"The invoice has a line called “{name}”, but no contract rule covers it.",
            "Ask the vendor what this line is for.",
        )
    if "requires delivery by" in low:
        return (
            "The order and the contract have different delivery dates",
            _sentence(text),
            "Check which date is the right one.",
        )
    if "is not on the purchase order" in low:
        return (
            "An invoice item is not on the purchase order",
            _sentence(text),
            "Ask the vendor why this item was billed.",
        )
    if "quantity" in low and "purchase order has" in low:
        return (
            "The quantity on the invoice differs from the order",
            _sentence(text),
            "Ask the vendor to correct the quantity, or confirm that the extra items were ordered.",
        )
    if "differs from the purchase order price" in low:
        return (
            "The price on the invoice differs from the order",
            _sentence(text),
            "Check which price is the right one.",
        )
    return (
        "Something needs a person's attention",
        _sentence(text),
        "Ask a person to look at it.",
    )


def review_note(reason: "ReviewReason") -> ReviewNote:
    """One review reason in plain words. The technical text is kept for a developer."""
    if reason.source == "contract":
        title, what, todo = _contract_note(reason.field, reason.reason)
    elif reason.source in ("invoice", "purchase_order"):
        noun = "invoice" if reason.source == "invoice" else "purchase order"
        title, what, todo = _document_note(noun, reason.field, reason.reason)
    else:
        title, what, todo = _audit_note(reason.reason)
    technical = f"{reason.field}: {reason.reason}" if reason.field else reason.reason
    return ReviewNote(
        group=GROUPS[reason.source], title=title, what=what, todo=todo, technical=technical
    )


def review_notes(out: "AuditOut") -> list[ReviewNote]:
    """Every review reason in plain words, grouped in a fixed order."""
    order = list(GROUPS.values())
    notes = [review_note(reason) for reason in out.review_reasons]
    return sorted(notes, key=lambda note: order.index(note.group))


# ---- the problems and the whole summary ----


class PlainProblem(BaseModel):
    """One thing that is wrong, written for a person who is not a technician."""

    clause_type: ClauseType
    title: str
    amount_text: str
    paragraphs: list[str]
    page: int
    quote: str


class PlainSummary(BaseModel):
    """The verdict, the problems, the sums, the checks and the open points in plain words."""

    headline: str
    advice: str
    problems: list[PlainProblem]
    calculation: list[CalcStep] = Field(default_factory=list)
    checks: list[CheckItem] = Field(default_factory=list)
    review_notes: list[ReviewNote] = Field(default_factory=list)


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
        calculation=calculation(out),
        checks=checks(out),
        review_notes=review_notes(out),
    )
