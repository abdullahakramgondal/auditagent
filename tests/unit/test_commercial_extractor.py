import json
from datetime import date
from decimal import Decimal

from auditagent.agents.commercial_extractor import CommercialExtractor
from auditagent.llm.fake import ScriptedProvider
from auditagent.schemas.document import PageText, ParsedDocument


def invoice_text(
    amount="10,000,000", adjustment="Less: volume discount -3,000,000\n", total="7,000,000"
):
    """The text of a layout 1 invoice; the amount of the row, the adjustment and the total can change."""
    return (
        "INVOICE\nInvoice No: INV-001\nInvoice Date: 26 October 2026\n"
        "Delivery Date: 25 October 2026\nDue Date: 25 November 2026\nBill To: Buyer Co\n"
        "From: Vendor Co\nItem Qty Unit Price (PKR) Amount (PKR)\n"
        f"Server 10 1,000,000 {amount}\n{adjustment}Total: PKR {total}\n"
    )


PO_TEXT = (
    "PURCHASE ORDER\nPO No: PO-2026-001\nPO Date: 01 September 2026\n"
    "Delivery Due Date: 15 October 2026\nBuyer: Buyer Co\nVendor: Vendor Co\n"
    "Item Qty Unit Price (PKR) Amount (PKR)\nServer 10 1,000,000 10,000,000\n"
    "Total: PKR 10,000,000\n"
)
GOOD_INVOICE = {
    "invoice_number": "INV-001",
    "invoice_date": "2026-10-26",
    "delivery_date": "2026-10-25",
    "due_date": "2026-11-25",
    "line_items": [
        {"item_name": "Server", "quantity": 10, "unit_price": 1000000, "line_total": 10000000}
    ],
    "adjustments": [{"label": "Less: volume discount", "amount": -3000000}],
    "total_amount": 7000000,
}
GOOD_PO = {
    "po_number": "PO-2026-001",
    "po_date": "2026-09-01",
    "delivery_due_date": "2026-10-15",
    "line_items": [
        {"item_name": "Server", "quantity": 10, "unit_price": 1000000, "line_total": 10000000}
    ],
    "total_amount": 10000000,
}


def doc(text):
    """A one-page document with this text (a page without text has no readable text)."""
    return ParsedDocument(
        source_name="d.pdf", sha256="d" * 64, pages=[PageText(number=1, text=text)]
    )


def invoice(replies, text=None):
    """Run Agent 2 on an invoice with a scripted model; returns the result and the provider."""
    provider = ScriptedProvider(replies)
    result = CommercialExtractor(provider).extract_invoice(
        doc(invoice_text() if text is None else text)
    )
    return result, provider


def order(replies, text=PO_TEXT):
    """Run Agent 2 on a purchase order with a scripted model; returns the result and the provider."""
    provider = ScriptedProvider(replies)
    return CommercialExtractor(provider).extract_purchase_order(doc(text)), provider


def issue_for(result, field):
    """The first issue reported for one field."""
    return next(i for i in result.issues if i.clause_type == field)


def test_a_correct_invoice_is_extracted_with_no_issues():
    result, provider = invoice([json.dumps(GOOD_INVOICE)])
    assert result.issues == [] and len(provider.prompts) == 1
    data = result.invoice
    assert data.invoice_number == "INV-001" and data.total_amount == Decimal(7000000)
    assert data.invoice_date == date(2026, 10, 26) and data.delivery_date == date(2026, 10, 25)
    assert data.due_date == date(2026, 11, 25)
    assert data.line_items[0].quantity == 10 and data.adjustments[0].amount == Decimal(-3000000)
    assert result.llm_model == "scripted-1"


def test_the_invoice_date_and_the_delivery_date_swapped_by_the_model_are_refused():
    """The delivery date decides the late penalty, so a swap must never pass."""
    swapped = {**GOOD_INVOICE, "invoice_date": "2026-10-25", "delivery_date": "2026-10-26"}
    result, _ = invoice([json.dumps(swapped)])
    assert result.invoice is None
    assert "labelled" in issue_for(result, "invoice_date").reason
    assert "labelled" in issue_for(result, "delivery_date").reason


def test_a_line_item_that_is_not_in_the_document_is_refused():
    invented = {
        **GOOD_INVOICE,
        "line_items": [
            *GOOD_INVOICE["line_items"],
            {"item_name": "Router", "quantity": 2, "unit_price": 5000, "line_total": 10000},
        ],
    }
    result, _ = invoice([json.dumps(invented)])
    assert result.invoice is None
    assert "Router" in issue_for(result, "line_items").reason


def test_a_total_that_is_not_on_the_total_line_is_refused():
    result, _ = invoice([json.dumps({**GOOD_INVOICE, "total_amount": 8000000})])
    assert result.invoice is None and "total_amount" in {i.clause_type for i in result.issues}


def test_a_none_for_a_date_the_document_shows_is_refused():
    result, _ = invoice([json.dumps({**GOOD_INVOICE, "delivery_date": None})])
    assert result.invoice is None
    assert "returned none" in issue_for(result, "delivery_date").reason


def test_a_none_for_a_date_the_document_does_not_show_is_accepted():
    text = invoice_text().replace("Delivery Date: 25 October 2026\n", "")
    result, _ = invoice([json.dumps({**GOOD_INVOICE, "delivery_date": None})], text=text)
    assert result.issues == [] and result.invoice.delivery_date is None


def test_a_row_amount_that_is_not_quantity_times_price_is_returned_with_an_issue():
    """The invoice itself is wrong: the data is kept and the problem is a review reason, not an error."""
    text = invoice_text(amount="9,000,000", adjustment="", total="9,000,000")
    printed = {
        **GOOD_INVOICE,
        "line_items": [
            {"item_name": "Server", "quantity": 10, "unit_price": 1000000, "line_total": 9000000}
        ],
        "adjustments": [],
        "total_amount": 9000000,
    }
    result, _ = invoice([json.dumps(printed)], text=text)
    assert result.invoice is not None
    assert [i.clause_type for i in result.issues] == ["line_total"]


def test_a_total_that_is_not_the_sum_of_the_rows_is_returned_with_an_issue():
    text = invoice_text(adjustment="", total="9,000,000")
    printed = {**GOOD_INVOICE, "adjustments": [], "total_amount": 9000000}
    result, _ = invoice([json.dumps(printed)], text=text)
    assert result.invoice is not None
    assert [i.clause_type for i in result.issues] == ["total_amount"]
    assert "10,000,000" in result.issues[0].reason


def test_unusable_model_output_is_retried_and_then_accepted():
    result, provider = invoice(["not json", json.dumps(GOOD_INVOICE)])
    assert result.issues == [] and len(provider.prompts) == 2
    assert "rejected" in provider.prompts[1]


def test_model_output_that_never_validates_gives_no_invoice_and_a_reason():
    result, _ = invoice(["bad", "bad", "bad"])
    assert result.invoice is None and "unusable" in issue_for(result, "document").reason


def test_a_document_without_text_is_reported_and_costs_no_model_call():
    result, provider = invoice([], text="")
    assert result.invoice is None and provider.prompts == []
    assert "no readable text" in issue_for(result, "document").reason


def test_a_correct_purchase_order_is_extracted_with_no_issues():
    result, _ = order([json.dumps(GOOD_PO)])
    assert result.issues == []
    data = result.purchase_order
    assert data.po_number == "PO-2026-001" and data.po_date == date(2026, 9, 1)
    assert data.delivery_due_date == date(2026, 10, 15) and data.total_amount == Decimal(10000000)


def test_a_purchase_order_with_swapped_dates_is_refused():
    swapped = {**GOOD_PO, "po_date": "2026-10-15", "delivery_due_date": "2026-09-01"}
    result, _ = order([json.dumps(swapped)])
    assert result.purchase_order is None
    assert {"po_date", "delivery_due_date"} <= {i.clause_type for i in result.issues}
