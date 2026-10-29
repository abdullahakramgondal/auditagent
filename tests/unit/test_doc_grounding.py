from datetime import date

import pytest

from auditagent.agents.doc_grounding import (
    adjustment_problem,
    date_is_labelled,
    is_written,
    item_problem,
    shows_a_date,
    text_lines,
    total_is_written,
)

LAYOUT_1 = text_lines(
    "INVOICE\nInvoice No: INV-001\nInvoice Date: 26 October 2026\n"
    "Delivery Date: 25 October 2026\nDue Date: 25 November 2026\nBill To: Buyer Co\n"
    "From: Vendor Co\nItem Qty Unit Price (PKR) Amount (PKR)\n"
    "Fortinet FortiGate 100F Firewall 10 1,000,000 10,000,000\n"
    "Less: volume discount -550,000\nTotal: PKR 9,450,000"
)
LAYOUT_3 = text_lines(
    "INVOICE\nInvoice #: INV-001\nIssued On: 26/10/2026\n1. Fortinet FortiGate 100F Firewall\n"
    "10 x PKR 1,000,000 = PKR 10,000,000\nLess: volume discount: -PKR 550,000\n"
    "Grand Total: PKR 9,450,000"
)
WRAPPED = text_lines(
    "Item Description Quantity Unit Price Line Amount\n"
    "Samsung 32-inch Monitor 12 PKR 58,000 PKR 696,000\n"
    "with Stand\nTotal payable: PKR 696,000"
)
WRAPPED_NAME = "Samsung 32-inch Monitor with Stand"


def test_lines_are_flattened_and_blank_lines_dropped():
    assert text_lines("  a   b \n\n c\u00a0d ") == ["a b", "c d"]


def test_a_text_is_found_ignoring_case_and_spacing():
    assert is_written("inv-001", LAYOUT_1) and is_written("INV-001", LAYOUT_3)
    assert not is_written("INV-002", LAYOUT_1)
    assert not is_written("", LAYOUT_1)


def test_a_date_must_sit_on_a_line_with_its_own_label():
    lines = text_lines("Invoice Date: 26 October 2026\nDelivery Date: 25 October 2026")
    assert date_is_labelled(date(2026, 10, 26), "invoice_date", lines)
    assert date_is_labelled(date(2026, 10, 25), "delivery_date", lines)
    assert not date_is_labelled(date(2026, 10, 25), "invoice_date", lines)  # swapped
    assert not date_is_labelled(date(2026, 10, 26), "delivery_date", lines)  # swapped


@pytest.mark.parametrize(
    ("line", "role", "day"),
    [
        ("Invoice Date: 26 October 2026", "invoice_date", date(2026, 10, 26)),
        ("Bill Date: 26-Oct-2026", "invoice_date", date(2026, 10, 26)),
        ("Issued On: 26/10/2026", "invoice_date", date(2026, 10, 26)),
        ("Delivered On: 25-Oct-2026", "delivery_date", date(2026, 10, 25)),
        ("Date of Delivery: 25/10/2026", "delivery_date", date(2026, 10, 25)),
        ("Date of Supply: 30 October 2026", "delivery_date", date(2026, 10, 30)),
        ("Supplied On: 30-Oct-2026", "delivery_date", date(2026, 10, 30)),
        ("Pay By: 25/11/2026", "due_date", date(2026, 11, 25)),
        ("Payment Due: 25-Nov-2026 Supplier: Vendor Co", "due_date", date(2026, 11, 25)),
        ("Order Date: 01-Sep-2026", "po_date", date(2026, 9, 1)),
        ("Required By: 15-Oct-2026", "delivery_due_date", date(2026, 10, 15)),
    ],
)
def test_the_labels_and_date_formats_of_all_three_layouts_are_read(line, role, day):
    assert date_is_labelled(day, role, text_lines(line))


def test_a_supplier_line_is_not_a_delivery_label():
    lines = text_lines("Supplier: Vendor Co 30 October 2026")
    assert not date_is_labelled(date(2026, 10, 30), "delivery_date", lines)


def test_an_order_date_is_not_the_delivery_due_date():
    lines = text_lines("PO Date: 01 September 2026\nDelivery Due Date: 15 October 2026")
    assert date_is_labelled(date(2026, 9, 1), "po_date", lines)
    assert date_is_labelled(date(2026, 10, 15), "delivery_due_date", lines)
    assert not date_is_labelled(date(2026, 10, 15), "po_date", lines)


def test_a_missing_date_is_noticed_only_when_the_document_shows_one_next_to_its_label():
    lines = text_lines("Delivery Date: 25 October 2026\nDue Date: on receipt")
    assert shows_a_date("delivery_date", lines)
    assert not shows_a_date("due_date", lines)
    assert not shows_a_date("delivery_date", text_lines("Invoice No: INV-001"))


def test_an_item_row_is_proven_in_the_table_layout():
    name = "Fortinet FortiGate 100F Firewall"
    assert item_problem(name, 10, 1000000.0, 10000000.0, LAYOUT_1) is None


def test_an_item_row_is_proven_when_the_numbers_are_on_the_next_line():
    name = "Fortinet FortiGate 100F Firewall"
    assert item_problem(name, 10, 1000000.0, 10000000.0, LAYOUT_3) is None


def test_a_wrong_quantity_is_named_in_the_problem():
    problem = item_problem("Fortinet FortiGate 100F Firewall", 12, 1000000.0, 10000000.0, LAYOUT_1)
    assert "quantity" in problem and "unit price" not in problem


def test_an_item_that_is_not_in_the_document_is_refused():
    assert "not written" in item_problem("Router", 1, 1000.0, 1000.0, LAYOUT_1)


def test_an_item_name_wrapped_over_two_lines_is_proven():
    assert item_problem(WRAPPED_NAME, 12, 58000.0, 696000.0, WRAPPED) is None


def test_a_wrapped_name_whose_rest_is_not_on_the_next_line_is_refused():
    lines = text_lines(
        "Samsung 32-inch Monitor 12 PKR 58,000 PKR 696,000\nTotal payable: PKR 696,000"
    )
    assert "not written" in item_problem(WRAPPED_NAME, 12, 58000.0, 696000.0, lines)


def test_a_wrapped_name_with_a_wrong_quantity_names_the_quantity():
    assert "quantity" in item_problem(WRAPPED_NAME, 11, 58000.0, 696000.0, WRAPPED)


def test_an_adjustment_needs_its_label_and_its_amount_on_one_line():
    assert adjustment_problem("Less: volume discount", -550000.0, LAYOUT_1) is None
    assert adjustment_problem("Less: volume discount", -550000.0, LAYOUT_3) is None
    assert "amount" in adjustment_problem("Less: volume discount", -600000.0, LAYOUT_1)
    assert "not written" in adjustment_problem("Less: rebate", -550000.0, LAYOUT_1)


def test_the_total_must_sit_on_a_total_line():
    assert total_is_written(9450000.0, LAYOUT_1) and total_is_written(9450000.0, LAYOUT_3)
    assert not total_is_written(10000000.0, LAYOUT_1)  # that is an amount of a row, not the total
