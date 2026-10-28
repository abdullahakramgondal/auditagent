from auditagent.agents.doc_grounding import text_lines
from data.commercial_b.check_document import review_text

SPEC = {
    "kind": "invoice",
    "document": {
        "invoice_number": "INV-1",
        "invoice_date": "2026-11-03",
        "delivery_date": None,
        "due_date": "2026-12-03",
        "line_items": [
            {
                "item_name": "Server X",
                "quantity": 2,
                "unit_price": "1000000",
                "line_total": "2000000",
            }
        ],
        "adjustments": [{"label": "Trade discount (5%)", "amount": "-100000"}],
        "total_amount": "1900000",
    },
}
CLEAN = (
    "INVOICE\nInvoice No: INV-1\nIssued: 3 November 2026\nPayment due by 3 December 2026\n"
    "Server X  2  1,000,000  2,000,000\nTrade discount (5%)  -100,000\n"
    "Amount payable: PKR 1,900,000"
)


def missing(report):
    """The labels of the required values that were not found."""
    return [label for label, evidence in report["required"] if not evidence]


def test_a_clean_document_has_every_value_and_nothing_extra():
    report = review_text(SPEC, text_lines(CLEAN))
    assert missing(report) == [] and report["unexpected"] == []
    assert "Issued: 3 November 2026" in [line for _, line in report["required"] if line]


def test_a_date_that_is_not_printed_is_not_required():
    labels = [label for label, _ in review_text(SPEC, text_lines(CLEAN))["required"]]
    assert not any(label.startswith("delivery_date") for label in labels)


def test_a_missing_total_is_reported():
    lines = text_lines(CLEAN.replace("Amount payable: PKR 1,900,000", "Thank you"))
    assert missing(review_text(SPEC, lines)) == ["total 1900000"]


def test_an_item_name_wrapped_over_two_lines_is_found():
    spec = {
        **SPEC,
        "document": {
            **SPEC["document"],
            "line_items": [
                {
                    "item_name": "Samsung 32-inch Monitor with Stand",
                    "quantity": 12,
                    "unit_price": "58000",
                    "line_total": "696000",
                }
            ],
            "adjustments": [],
            "total_amount": "696000",
        },
    }
    text = (
        "Invoice No: INV-1\nIssued: 3 November 2026\nDue: 3 December 2026\n"
        "Samsung 32-inch Monitor  12  58,000  696,000\nwith Stand\nTotal: PKR 696,000"
    )
    assert missing(review_text(spec, text_lines(text))) == []


def test_an_extra_charge_is_reported_with_its_line():
    lines = text_lines(CLEAN + "\nHandling fee  5,000")
    unexpected = review_text(SPEC, lines)["unexpected"]
    assert unexpected == [("Handling fee 5,000", "5,000")]


def test_the_subtotal_is_not_an_unexpected_amount():
    assert review_text(SPEC, text_lines(CLEAN + "\nSubtotal  2,000,000"))["unexpected"] == []
