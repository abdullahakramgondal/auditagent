from auditagent.schemas.extraction import ExtractionIssue
from auditagent.schemas.invoice import InvoiceData, PurchaseOrderData
from eval.agent2_eval import AGENT2_CODE_FOLDERS
from eval.agent2_scoring import aggregate, differences, score_document

ROW = {"item_name": "Server", "quantity": 10, "unit_price": "1000000", "line_total": "10000000"}
GOLD_INVOICE = {
    "invoice_number": "INV-001",
    "invoice_date": "2026-10-26",
    "delivery_date": "2026-10-25",
    "line_items": [ROW],
    "adjustments": [{"label": "Less: volume discount", "amount": "-3000000"}],
    "total_amount": "7000000",
}
GOLD_PO = {
    "po_number": "PO-2026-001",
    "po_date": "2026-09-01",
    "delivery_due_date": "2026-10-15",
    "line_items": [ROW],
    "total_amount": "10000000",
}


def invoice(**changes):
    """The invoice of the answer key, with some fields changed."""
    return InvoiceData.model_validate({**GOLD_INVOICE, **changes})


def issue(text="needs review"):
    """One issue about the total of a document."""
    return ExtractionIssue(clause_type="total_amount", reason=text)


def test_a_document_equal_to_the_key_is_correct():
    entry = score_document("invoice", GOLD_INVOICE, invoice(), [])
    assert entry["status"] == "correct" and entry["issues"] == 0
    assert all(entry["fields"].values()) and entry["differences"] == {}


def test_money_is_compared_as_a_number_so_a_trailing_zero_does_not_matter():
    row = {**ROW, "unit_price": "1000000.0", "line_total": "10000000.0"}
    entry = score_document("invoice", GOLD_INVOICE, invoice(line_items=[row]), [])
    assert entry["status"] == "correct"


def test_a_wrong_value_is_named_with_what_was_expected_and_what_was_found():
    entry = score_document("invoice", GOLD_INVOICE, invoice(total_amount="6000000"), [])
    assert entry["status"] == "wrong"
    assert entry["fields"]["total_amount"] is False and entry["fields"]["invoice_number"] is True
    assert entry["differences"] == {"total_amount": ("7000000", "6000000")}


def test_swapped_dates_are_two_wrong_fields():
    swapped = invoice(invoice_date="2026-10-25", delivery_date="2026-10-26")
    assert set(differences("invoice", GOLD_INVOICE, swapped)) == {"invoice_date", "delivery_date"}


def test_a_document_that_was_not_extracted_is_refused():
    entry = score_document("invoice", GOLD_INVOICE, None, [issue()])
    assert entry == {"issues": 1, "status": "refused"}


def test_a_purchase_order_is_scored_with_its_own_fields():
    order = PurchaseOrderData.model_validate(GOLD_PO)
    entry = score_document("purchase_order", GOLD_PO, order, [])
    assert entry["status"] == "correct" and "po_number" in entry["fields"]
    assert "invoice_number" not in entry["fields"]


def test_the_summary_counts_recall_precision_and_field_accuracy():
    order = PurchaseOrderData.model_validate(GOLD_PO)
    ok_invoice = score_document("invoice", GOLD_INVOICE, invoice(), [])
    ok_order = score_document("purchase_order", GOLD_PO, order, [])
    bad_invoice = score_document("invoice", GOLD_INVOICE, invoice(total_amount="6000000"), [])
    no_order = score_document("purchase_order", GOLD_PO, None, [issue()])
    flagged_invoice = score_document("invoice", GOLD_INVOICE, invoice(), [issue()])
    summary = aggregate(
        [
            {"invoice": ok_invoice, "purchase_order": ok_order},
            {"invoice": bad_invoice, "purchase_order": no_order},
            {"invoice": flagged_invoice, "purchase_order": ok_order},
        ]
    )
    inv, po, everything = summary["invoice"], summary["purchase_order"], summary["ALL"]
    assert (inv["docs"], inv["correct"], inv["wrong"], inv["refused"]) == (3, 2, 1, 0)
    assert inv["correct_with_issues"] == 1
    assert inv["recall"] == 0.667 and inv["precision"] == 0.667
    assert inv["field_accuracy"] == 0.952  # 20 of 21 fields
    assert (po["docs"], po["correct"], po["wrong"], po["refused"]) == (3, 2, 0, 1)
    assert po["recall"] == 0.667 and po["precision"] == 1.0 and po["field_accuracy"] == 1.0
    assert (everything["docs"], everything["correct"]) == (6, 4)
    assert everything["recall"] == 0.667 and everything["precision"] == 0.8
    assert everything["field_accuracy"] == 0.968  # 30 of 31 fields


def test_nothing_scored_gives_no_ratios():
    summary = aggregate([])
    assert summary["ALL"]["docs"] == 0 and summary["ALL"]["recall"] is None


def test_the_agent2_cache_fingerprint_covers_the_document_generator():
    assert all(folder.is_dir() for folder in AGENT2_CODE_FOLDERS)
    assert "generator" in {folder.name for folder in AGENT2_CODE_FOLDERS}
