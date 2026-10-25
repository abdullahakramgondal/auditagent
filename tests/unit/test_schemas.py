from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from auditagent.schemas.contract import ExtractedContract, LatePenaltyRule

CASE_A_RULE = {
    "clause_type": "late_penalty",
    "deadline": "2026-10-15",
    "mode": "flat_percent",
    "percent": "10",
    "source": {
        "page": 4,
        "text": "If delivery is later than 15 Oct 2026, a 10% penalty applies.",
    },
}


def test_case_a_rule_parses():
    contract = ExtractedContract.model_validate({"rules": [CASE_A_RULE]})
    rule = contract.rules[0]
    assert isinstance(rule, LatePenaltyRule)
    assert rule.percent == Decimal(10)
    assert rule.deadline == date(2026, 10, 15)


def test_percent_above_100_is_rejected():
    bad = {**CASE_A_RULE, "percent": "150"}
    with pytest.raises(ValidationError):
        ExtractedContract.model_validate({"rules": [bad]})


def test_missing_source_is_rejected():
    bad = {k: v for k, v in CASE_A_RULE.items() if k != "source"}
    with pytest.raises(ValidationError):
        ExtractedContract.model_validate({"rules": [bad]})
