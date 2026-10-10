from decimal import Decimal

import pytest
from pydantic import ValidationError

from auditagent.schemas.audit import AuditResult
from auditagent.schemas.invoice import InvoiceData

CASE_A_INVOICE = {
    "invoice_number": "INV-001",
    "invoice_date": "2026-10-26",
    "delivery_date": "2026-10-25",
    "line_items": [
        {
            "item_name": "Server",
            "quantity": 10,
            "unit_price": "1000000",
            "line_total": "10000000",
        }
    ],
    "total_amount": "10000000",
}

CASE_A_SOURCE = {
    "page": 4,
    "text": "If delivery is later than 15 Oct 2026, a 10% penalty applies.",
}

CASE_A_RESULT = {
    "status": "NON_COMPLIANT",
    "billed_total": "10000000",
    "correct_payable": "9000000",
    "total_difference": "1000000",
    "findings": [
        {
            "clause_type": "late_penalty",
            "description": "Delivered 10 days late; 10% penalty not applied.",
            "source": CASE_A_SOURCE,
            "expected_amount": "9000000",
            "billed_amount": "10000000",
            "difference": "1000000",
        }
    ],
}


def test_case_a_invoice_parses():
    invoice = InvoiceData.model_validate(CASE_A_INVOICE)
    assert invoice.total_amount == Decimal("10000000")
    assert invoice.line_items[0].quantity == 10


def test_zero_quantity_is_rejected():
    bad = {**CASE_A_INVOICE}
    bad["line_items"] = [{**CASE_A_INVOICE["line_items"][0], "quantity": 0}]
    with pytest.raises(ValidationError):
        InvoiceData.model_validate(bad)


def test_case_a_audit_result_is_valid():
    result = AuditResult.model_validate(CASE_A_RESULT)
    assert result.status == "NON_COMPLIANT"
    assert result.total_difference == Decimal("1000000")


def test_compliant_with_findings_is_rejected():
    bad = {**CASE_A_RESULT, "status": "COMPLIANT"}
    with pytest.raises(ValidationError):
        AuditResult.model_validate(bad)


def test_non_compliant_without_findings_is_rejected():
    bad = {**CASE_A_RESULT, "findings": []}
    with pytest.raises(ValidationError):
        AuditResult.model_validate(bad)