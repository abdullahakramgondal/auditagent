"""The words of a finding: percentages are written without a trailing zero (TODO item 36)."""

from datetime import date
from decimal import Decimal

from auditagent.rules.engine import audit_invoice, pct
from auditagent.schemas.contract import (
    ExtractedContract,
    LatePenaltyRule,
    Source,
    VolumeDiscountRule,
)
from auditagent.schemas.invoice import InvoiceData

SOURCE = Source(page=4, text="The clause text.")
INVOICE = InvoiceData.model_validate(
    {
        "invoice_number": "INV-1",
        "invoice_date": "2026-10-26",
        "delivery_date": "2026-10-25",
        "line_items": [
            {
                "item_name": "Server",
                "quantity": 60,
                "unit_price": "1000000",
                "line_total": "60000000",
            }
        ],
        "total_amount": "60000000",
    }
)


def test_a_percentage_loses_its_trailing_zero_and_keeps_its_decimals():
    assert pct(Decimal("15.0")) == "15"
    assert pct(Decimal("2.50")) == "2.5"
    assert pct(Decimal("0.5")) == "0.5"
    assert pct(Decimal(100)) == "100"


def test_the_description_of_a_late_penalty_says_15_not_15_point_0():
    rule = LatePenaltyRule(
        deadline=date(2026, 10, 15),
        mode="flat_percent",
        percent=Decimal("15.0"),
        source=SOURCE,
    )
    text = audit_invoice(ExtractedContract(rules=[rule]), INVOICE).findings[0].description
    assert "15%" in text and "15.0%" not in text


def test_the_description_of_a_volume_discount_says_10_not_10_point_0():
    rule = VolumeDiscountRule(min_quantity=20, discount_percent=Decimal("10.0"), source=SOURCE)
    text = audit_invoice(ExtractedContract(rules=[rule]), INVOICE).findings[0].description
    assert "10% from 20 units" in text
