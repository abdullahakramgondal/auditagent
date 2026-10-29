"""The pipeline with a scripted model, the purchase order cross-check, and the amounts of AuditResult."""

import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from auditagent.agents.commercial_extractor import CommercialExtractor
from auditagent.agents.legal_extractor import LegalExtractor
from auditagent.ingestion.embedder import HashingEmbedder
from auditagent.llm.fake import ScriptedProvider
from auditagent.pipeline.run import audit_documents
from auditagent.rules.cross_check import po_review_reasons
from auditagent.schemas.audit import AuditResult
from auditagent.schemas.contract import ExtractedContract
from auditagent.schemas.document import PageText, ParsedDocument
from auditagent.schemas.invoice import InvoiceData, PurchaseOrderData

LATE_Q = (
    "If delivery of the goods is later than 15 October 2026, "
    "a penalty of 10% shall apply to the final invoice."
)
CONTRACT_PAGES = [
    "SUPPLY AGREEMENT\n1. Parties\nThis Agreement is between Buyer Co and Vendor Co.\nPage 1 of 2",
    f"SUPPLY AGREEMENT\n3. Late Delivery\n{LATE_Q}\nPage 2 of 2",
]
NO_CLAUSES = ["SUPPLY AGREEMENT\n1. Parties\nThis Agreement is between Buyer Co and Vendor Co."]
INVOICE_TEXT = (
    "INVOICE\nInvoice No: INV-001\nInvoice Date: 26 October 2026\n"
    "Delivery Date: 25 October 2026\nDue Date: 25 November 2026\nBill To: Buyer Co\n"
    "From: Vendor Co\nItem Qty Unit Price (PKR) Amount (PKR)\n"
    "Server 10 1,000,000 10,000,000\nTotal: PKR 10,000,000\n"
)
PO_TEXT = (
    "PURCHASE ORDER\nPO No: PO-2026-001\nPO Date: 01 September 2026\n"
    "Delivery Due Date: 15 October 2026\nBuyer: Buyer Co\nVendor: Vendor Co\n"
    "Item Qty Unit Price (PKR) Amount (PKR)\nServer 10 1,000,000 10,000,000\n"
    "Total: PKR 10,000,000\n"
)
ROW = {"item_name": "Server", "quantity": 10, "unit_price": 1000000, "line_total": 10000000}
LATE = {
    "quote": LATE_Q,
    "chunk_id": "x-002",
    "deadline_quote": LATE_Q,
    "deadline": "2026-10-15",
    "mode": "flat_percent",
    "percent": 10,
    "cap_percent": None,
    "grace_days": 0,
}
INVOICE = {
    "invoice_number": "INV-001",
    "invoice_date": "2026-10-26",
    "delivery_date": "2026-10-25",
    "due_date": "2026-11-25",
    "line_items": [ROW],
    "adjustments": [],
    "total_amount": 10000000,
}
PO = {
    "po_number": "PO-2026-001",
    "po_date": "2026-09-01",
    "delivery_due_date": "2026-10-15",
    "line_items": [ROW],
    "total_amount": 10000000,
}
EMPTY = json.dumps({"rules": []})


def doc(pages):
    return ParsedDocument(
        source_name="d.pdf",
        sha256="d" * 64,
        pages=[PageText(number=i, text=t) for i, t in enumerate(pages, start=1)],
    )


def run(replies, contract_pages=CONTRACT_PAGES, po_text=PO_TEXT):
    """Agent 1 asks 4 questions (one per clause type), then Agent 2 reads the invoice and the order."""
    provider = ScriptedProvider(replies)
    legal = LegalExtractor(provider, HashingEmbedder())
    commercial = CommercialExtractor(provider)
    return audit_documents(
        doc(contract_pages), doc([po_text]), doc([INVOICE_TEXT]), legal, commercial
    )


def legal_replies(*late_rules):
    return [json.dumps({"rules": list(late_rules)}), EMPTY, EMPTY, EMPTY]


def test_a_late_invoice_gives_a_finding_with_its_clause_and_no_review_reason():
    report = run([*legal_replies(LATE), json.dumps(INVOICE), json.dumps(PO)])
    result = report.result
    assert result.status == "NON_COMPLIANT" and result.review_reasons == []
    assert result.billed_total == Decimal(10000000)
    assert result.correct_payable == Decimal(9000000)
    assert result.total_difference == Decimal(1000000)
    assert result.findings[0].source.page == 2 and result.findings[0].source.text == LATE_Q
    assert report.invoice.invoice_number == "INV-001" and report.purchase_order is not None


def test_a_purchase_order_with_another_delivery_date_is_a_review_reason_next_to_the_finding():
    po_text = PO_TEXT.replace("15 October 2026", "20 October 2026")
    po = {**PO, "delivery_due_date": "2026-10-20"}
    report = run([*legal_replies(LATE), json.dumps(INVOICE), json.dumps(po)], po_text=po_text)
    assert report.result.status == "NON_COMPLIANT"
    assert any("20 October 2026" in reason for reason in report.result.review_reasons)


def test_an_invoice_that_cannot_be_proven_gives_needs_review_without_amounts():
    report = run([*legal_replies(LATE), "bad", "bad", "bad", json.dumps(PO)])
    result = report.result
    assert result.status == "NEEDS_REVIEW" and report.invoice is None
    assert result.billed_total is None and result.total_difference is None
    assert any(reason.startswith("invoice:") for reason in result.review_reasons)


def test_a_purchase_order_that_cannot_be_proven_does_not_stop_the_audit():
    report = run([*legal_replies(LATE), json.dumps(INVOICE), "bad", "bad", "bad"])
    assert report.result.status == "NON_COMPLIANT" and report.purchase_order is None
    assert any("purchase order" in reason for reason in report.result.review_reasons)


def test_a_contract_without_any_rule_needs_review_and_is_never_compliant():
    replies = [EMPTY, EMPTY, EMPTY, EMPTY, json.dumps(INVOICE), json.dumps(PO)]
    report = run(replies, contract_pages=NO_CLAUSES)
    assert report.result.status == "NEEDS_REVIEW"
    assert any("No audit rule" in reason for reason in report.result.review_reasons)


# ---- the cross-check of the purchase order ----


def contract_with(*rules):
    placeholder = {"page": 1, "text": "placeholder"}
    return ExtractedContract.model_validate(
        {"rules": [{**r, "source": placeholder} for r in rules]}
    )


def invoice_of(*rows):
    return InvoiceData.model_validate({**INVOICE, "line_items": list(rows) or [ROW]})


def order_of(*rows):
    return PurchaseOrderData.model_validate({**PO, "line_items": list(rows) or [ROW]})


def row(name="Server", quantity=10, price=1000000):
    return {
        "item_name": name,
        "quantity": quantity,
        "unit_price": price,
        "line_total": quantity * price,
    }


LATE_RULE = {
    "clause_type": "late_penalty",
    "deadline": "2026-10-15",
    "mode": "flat_percent",
    "percent": "10",
}
PRICE_RULE = {"clause_type": "unit_price", "item_name": "Server", "agreed_unit_price": "1000000"}


def test_a_matching_order_gives_no_reason():
    assert po_review_reasons(contract_with(LATE_RULE), invoice_of(), order_of()) == []


def test_a_delivery_date_of_the_order_that_differs_from_the_contract_deadline():
    order = PurchaseOrderData.model_validate({**PO, "delivery_due_date": "2026-10-20"})
    reasons = po_review_reasons(contract_with(LATE_RULE), invoice_of(), order)
    assert len(reasons) == 1 and "15 October 2026" in reasons[0]


def test_an_invoice_item_that_is_not_on_the_order():
    reasons = po_review_reasons(contract_with(), invoice_of(row("Router")), order_of())
    assert len(reasons) == 1 and "not on the purchase order" in reasons[0]


def test_a_different_quantity_is_a_reason():
    reasons = po_review_reasons(contract_with(), invoice_of(row(quantity=12)), order_of())
    assert len(reasons) == 1 and "quantity" in reasons[0]


def test_a_different_price_is_a_reason_when_no_unit_price_rule_covers_the_item():
    reasons = po_review_reasons(contract_with(), invoice_of(row(price=1100000)), order_of())
    assert len(reasons) == 1 and "unit price" in reasons[0]


def test_a_different_price_is_not_counted_twice_when_a_unit_price_rule_covers_the_item():
    reasons = po_review_reasons(
        contract_with(PRICE_RULE), invoice_of(row(price=1100000)), order_of()
    )
    assert reasons == []


# ---- a result without amounts ----


def test_only_a_needs_review_result_may_have_no_amounts():
    assert AuditResult(status="NEEDS_REVIEW", review_reasons=["invoice: not proven"])
    with pytest.raises(ValidationError):
        AuditResult(status="COMPLIANT")
