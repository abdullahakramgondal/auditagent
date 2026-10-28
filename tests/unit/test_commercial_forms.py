import json

import pytest

from auditagent.agents.commercial_forms import InvoiceForm, PurchaseOrderForm


@pytest.mark.parametrize("form", [InvoiceForm, PurchaseOrderForm])
def test_form_schema_avoids_keywords_gemini_rejects(form):
    """Gemini's response schema rejects exclusive bounds and defaults; use ge/le and required keys."""
    text = json.dumps(form.model_json_schema())
    for banned in ("exclusiveMinimum", "exclusiveMaximum", '"default"'):
        assert banned not in text


def test_an_invoice_date_that_may_be_missing_must_still_be_stated_as_null():
    required = InvoiceForm.model_json_schema()["required"]
    assert "delivery_date" in required and "due_date" in required


def test_the_adjustments_list_must_be_stated_even_when_it_is_empty():
    assert "adjustments" in InvoiceForm.model_json_schema()["required"]


def test_a_purchase_order_delivery_date_must_be_stated_even_when_it_is_null():
    assert "delivery_due_date" in PurchaseOrderForm.model_json_schema()["required"]
