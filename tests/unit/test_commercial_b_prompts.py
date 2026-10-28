from decimal import Decimal

from auditagent.schemas.invoice import InvoiceData, PurchaseOrderData
from data.commercial_b.make_prompts import SPECS, build_prompt, describe_document

MODELS = {"invoice": InvoiceData, "purchase_order": PurchaseOrderData}


def spec_named(case_id):
    """The spec with this id."""
    return next(spec for spec in SPECS if spec["case_id"] == case_id)


def test_there_are_eight_documents_with_unique_ids_and_unique_shapes():
    assert [s["case_id"] for s in SPECS] == [f"cb_0{n}" for n in range(1, 9)]
    assert len({s["shape"] for s in SPECS}) == 8


def test_both_kinds_and_both_writers_are_used():
    assert {s["kind"] for s in SPECS} == {"invoice", "purchase_order"}
    assert {s["writer"] for s in SPECS} == {"claude", "chatgpt"}


def test_every_answer_key_is_a_valid_document():
    for spec in SPECS:
        MODELS[spec["kind"]].model_validate(spec["document"])


def test_the_rows_and_the_total_of_every_answer_key_add_up():
    for spec in SPECS:
        doc = spec["document"]
        for item in doc["line_items"]:
            assert item["quantity"] * Decimal(item["unit_price"]) == Decimal(item["line_total"])
        rows = sum(Decimal(item["line_total"]) for item in doc["line_items"])
        adjustments = sum(Decimal(a["amount"]) for a in doc.get("adjustments", []))
        assert rows + adjustments == Decimal(doc["total_amount"]), spec["case_id"]


def test_the_prompt_states_every_value_exactly():
    for spec in SPECS:
        prompt = build_prompt(spec)
        doc = spec["document"]
        assert spec["buyer"] in prompt and spec["vendor"] in prompt
        for item in doc["line_items"]:
            assert item["item_name"] in prompt
            assert f"{int(item['line_total']):,}" in prompt
        assert f"{int(doc['total_amount']):,}" in prompt
        for adjustment in doc.get("adjustments", []):
            assert adjustment["label"] in prompt
        for note in spec.get("style_notes", []):
            assert note in prompt


def test_a_date_that_is_not_printed_is_stated_as_not_printed():
    assert "No payment due date is printed" in build_prompt(spec_named("cb_07"))
    assert "No payment due date" not in build_prompt(spec_named("cb_01"))


def test_the_subtotal_is_stated_when_there_are_adjustments():
    lines = describe_document(spec_named("cb_05"))
    assert "The items add up to PKR 1,895,000 before the adjustments below." in lines
    assert any("'Sales Tax (18%)'" in line and "it is added" in line for line in lines)
    assert any("it is deducted" in line for line in describe_document(spec_named("cb_03")))
    assert not any("add up" in line for line in describe_document(spec_named("cb_02")))
