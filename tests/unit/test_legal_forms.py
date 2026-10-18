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