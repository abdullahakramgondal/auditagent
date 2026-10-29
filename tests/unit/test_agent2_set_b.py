from auditagent.schemas.invoice import InvoiceData, PurchaseOrderData
from data.commercial_b.make_prompts import SPECS
from eval.agent2_scoring import score_document
from eval.agent2_set_b_eval import RESULT_CLASSES, SET_DIR, document_of

MODELS = {"invoice": InvoiceData, "purchase_order": PurchaseOrderData}


def spec_named(case_id):
    """The spec with this id."""
    return next(spec for spec in SPECS if spec["case_id"] == case_id)


def test_every_answer_key_scores_as_correct_against_itself():
    for spec in SPECS:
        data = MODELS[spec["kind"]].model_validate(spec["document"])
        entry = score_document(spec["kind"], spec["document"], data, [])
        assert entry["status"] == "correct", spec["case_id"]


def test_an_invoice_without_the_delivery_date_that_the_key_has_is_wrong_not_refused():
    """A document that comes out with a date missing must show up as a wrong field, never as a pass."""
    spec = spec_named("cb_01")
    data = InvoiceData.model_validate({**spec["document"], "delivery_date": None})
    entry = score_document("invoice", spec["document"], data, [])
    assert entry["status"] == "wrong" and set(entry["differences"]) == {"delivery_date"}


def test_the_result_of_each_kind_hands_back_its_own_document():
    invoice = InvoiceData.model_validate(spec_named("cb_01")["document"])
    order = PurchaseOrderData.model_validate(spec_named("cb_02")["document"])
    invoice_result = RESULT_CLASSES["invoice"](invoice=invoice, llm_model="m")
    order_result = RESULT_CLASSES["purchase_order"](purchase_order=order, llm_model="m")
    assert document_of("invoice", invoice_result) == invoice
    assert document_of("purchase_order", order_result) == order
    assert document_of("invoice", RESULT_CLASSES["invoice"](llm_model="m")) is None
    assert SET_DIR.name == "commercial_b"
