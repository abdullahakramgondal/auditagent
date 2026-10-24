import json

import pytest

from auditagent.agents.legal_forms import (
    LateRulesForm,
    PaymentRulesForm,
    PriceRulesForm,
    VolumeRulesForm,
)

FORMS = [LateRulesForm, VolumeRulesForm, PaymentRulesForm, PriceRulesForm]


@pytest.mark.parametrize("form", FORMS)
def test_form_schema_avoids_keywords_gemini_rejects(form):
    """Gemini's response schema rejects exclusive bounds and defaults; use ge/le and required keys."""
    text = json.dumps(form.model_json_schema())
    for banned in ("exclusiveMinimum", "exclusiveMaximum", '"default"'):
        assert banned not in text


def test_cap_percent_must_be_stated_even_when_it_is_null():
    schema = LateRulesForm.model_json_schema()
    assert "cap_percent" in schema["$defs"]["LateRuleForm"]["required"]


def test_deadline_quote_is_required_and_comes_before_the_deadline():
    """The model copies the sentence first, then reads the date from it."""
    late = LateRulesForm.model_json_schema()["$defs"]["LateRuleForm"]
    assert "deadline_quote" in late["required"]
    keys = list(late["properties"])
    assert keys.index("deadline_quote") < keys.index("deadline")