"""Checks that make every value of an invoice or a purchase order prove itself against the document text.

The checks work on the lines of the document: a value must be written where the document puts it
(a date next to its label, the amounts on the row of their item), not just somewhere on the page.
A label that these patterns do not know is refused, which becomes a review reason: it is never guessed.
"""

import re
from datetime import date

from auditagent.agents.grounding import date_in, number_in
from auditagent.ingestion.pdf_parser import normalize_for_match

# The words that label each date. Layouts say "Invoice Date", "Bill Date" or "Issued On";
# "Delivery Date", "Delivered On" or "Date of Delivery"; "Due Date", "Payment Due" or "Pay By"; and for
# an order "PO Date", "Order Date" or "Raised On"; "Delivery Due Date", "Required By" or "Deliver By".
DATE_LABELS = {
    "invoice_date": re.compile(r"\b(?:invoice|bill|issued?|dated)\b", re.IGNORECASE),
    "delivery_date": re.compile(r"\bdeliver\w*", re.IGNORECASE),
    "due_date": re.compile(r"\b(?:due|pay|payable|payment)\b", re.IGNORECASE),
    "po_date": re.compile(r"\b(?:po|purchase\s+order|order|raised|issued?|dated)\b", re.IGNORECASE),
    "delivery_due_date": re.compile(r"\b(?:deliver\w*|required)\b", re.IGNORECASE),
}
_TOTAL_LABEL = re.compile(r"\b(?:total|payable|amount\s+due|balance)\b", re.IGNORECASE)
# A date written in any of the three layouts: 25 October 2026, 25-Oct-2026, 25/10/2026, 2026-10-25.
_ANY_DATE = re.compile(r"\b\d{1,2}[-/ ](?:[A-Za-z]{3,9}|\d{1,2})[-/ ]\d{4}\b|\b\d{4}-\d{2}-\d{2}\b")


def text_lines(text: str) -> list[str]:
    """The non-empty lines of a document with the spacing flattened."""
    return [line for line in (normalize_for_match(raw) for raw in text.splitlines()) if line]


def is_written(value: str, lines: list[str]) -> bool:
    """True if the text (an invoice number, say) is written on one line, ignoring case and spacing."""
    wanted = normalize_for_match(value).lower()
    return bool(wanted) and any(wanted in line.lower() for line in lines)


def date_is_labelled(day: date, role: str, lines: list[str]) -> bool:
    """True if `day` is written on a line that carries a label for this role (in any of the date layouts)."""
    label = DATE_LABELS[role]
    return any(label.search(line) and date_in(day, line) for line in lines)


def shows_a_date(role: str, lines: list[str]) -> bool:
    """True if some line has a label for this role and a date: a model that returned none missed it."""
    label = DATE_LABELS[role]
    return any(label.search(line) and _ANY_DATE.search(line) for line in lines)


def total_is_written(value: float, lines: list[str]) -> bool:
    """True if the amount is written on a line that says total (or payable, or amount due)."""
    return any(_TOTAL_LABEL.search(line) and number_in(value, line) for line in lines)


def item_problem(name: str, quantity: int, unit_price: float, line_total: float, lines: list[str]):
    """Why this item row cannot be proven, or None if it can.

    The name, the quantity, the unit price and the amount must be written on the row of the item. A layout
    may print the numbers on the line below the name, so the line after the name is part of the row.
    """
    wanted = normalize_for_match(name).lower()
    rows = [" ".join(lines[i : i + 2]) for i, line in enumerate(lines) if wanted in line.lower()]
    if not rows:
        return f"item {name!r} is not written in the document"
    checks = (("quantity", quantity), ("unit price", unit_price), ("amount", line_total))
    fewest_missing = None
    for row in rows:
        missing = [label for label, value in checks if not number_in(value, row)]
        if not missing:
            return None
        if fewest_missing is None or len(missing) < len(fewest_missing):
            fewest_missing = missing
    return f"{', '.join(fewest_missing)} of item {name!r} not written on its row"


def adjustment_problem(label: str, amount: float, lines: list[str]):
    """Why this adjustment (a discount or charge) cannot be proven, or None if it can.

    The label must be written, and the amount (without its sign) must be on the same line.
    The sign is not checked here: a wrong sign makes the invoice arithmetic fail.
    """
    wanted = normalize_for_match(label).lower()
    holders = [line for line in lines if wanted in line.lower()]
    if not holders:
        return f"adjustment {label!r} is not written in the document"
    if not any(number_in(abs(amount), line) for line in holders):
        return f"amount {abs(amount)} of adjustment {label!r} is not written on its line"
    return None
