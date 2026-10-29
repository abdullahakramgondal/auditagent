"""Compare the purchase order with the invoice and the contract. Pure code, no LLM.

Every difference is a review reason, never a finding: the purchase order is not a rule of the contract.
"""

from datetime import date

from auditagent.rules.engine import same_item
from auditagent.schemas.contract import ExtractedContract, LatePenaltyRule, UnitPriceRule
from auditagent.schemas.invoice import InvoiceData, PurchaseOrderData


def _day(value: date) -> str:
    return f"{value.day} {value:%B %Y}"


def po_review_reasons(
    contract: ExtractedContract, invoice: InvoiceData, order: PurchaseOrderData
) -> list[str]:
    """What does not agree between the purchase order, the invoice and the contract."""
    reasons = []
    agreed = [rule for rule in contract.rules if isinstance(rule, UnitPriceRule)]

    if order.delivery_due_date is not None:
        for rule in contract.rules:
            if isinstance(rule, LatePenaltyRule) and rule.deadline != order.delivery_due_date:
                reasons.append(
                    f"The purchase order requires delivery by {_day(order.delivery_due_date)} "
                    f"but the contract penalty deadline is {_day(rule.deadline)}."
                )

    for item in invoice.line_items:
        ordered = next(
            (row for row in order.line_items if same_item(row.item_name, item.item_name)), None
        )
        if ordered is None:
            reasons.append(f"The invoice item {item.item_name!r} is not on the purchase order.")
            continue
        if item.quantity != ordered.quantity:
            reasons.append(
                f"Item {item.item_name!r}: the invoice has quantity {item.quantity} "
                f"but the purchase order has {ordered.quantity}."
            )
        # A price above the agreed unit price is already a finding: do not count it twice.
        explained = any(same_item(rule.item_name, item.item_name) for rule in agreed)
        if item.unit_price != ordered.unit_price and not explained:
            reasons.append(
                f"Item {item.item_name!r}: the invoice unit price {item.unit_price:,.2f} "
                f"differs from the purchase order price {ordered.unit_price:,.2f}."
            )
    return reasons
