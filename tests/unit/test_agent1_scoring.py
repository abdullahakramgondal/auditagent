from datetime import date
from decimal import Decimal

from auditagent.schemas.contract import (
    ExtractedContract,
    LatePenaltyRule,
    Source,
    UnitPriceRule,
    VolumeDiscountRule,
)
from auditagent.schemas.extraction import AgentOneResult, ExtractionIssue
from eval.agent1_scoring import aggregate, score_case

LATE_Q = "If delivery of the goods is later than 15 October 2026, a penalty of 10% shall apply."
VOL_Q = "A volume discount of 5% is granted on any order of 25 units or above."

SPEC = {
    "rules": [
        {"clause_type": "late_penalty", "deadline": "2026-10-15", "mode": "flat_percent", "percent": "10", "grace_days": 0},
        {"clause_type": "volume_discount", "min_quantity": 25, "discount_percent": "5"},
    ]
}
GOLD_SOURCES = {
    "late_penalty": {"page": 4, "text": LATE_Q},
    "volume_discount": {"page": 6, "text": VOL_Q},
}


def late(percent="10", page=4, quote="3. Delivery " + LATE_Q, grace=0, cap=None):
    return LatePenaltyRule(deadline=date(2026, 10, 15), mode="flat_percent", percent=Decimal(percent),
                           cap_percent=cap, grace_days=grace, source=Source(page=page, text=quote))


def volume(page=6):
    return VolumeDiscountRule(min_quantity=25, discount_percent=Decimal("5.0"), source=Source(page=page, text=VOL_Q))


def result(rules, issues=()):
    return AgentOneResult(contract=ExtractedContract(rules=list(rules)), issues=list(issues), llm_model="m")


def test_perfect_result_is_correct_everywhere():
    scored = score_case(SPEC, result([late(), volume()]), GOLD_SOURCES)
    assert scored["late_penalty"]["status"] == "correct"
    assert scored["late_penalty"]["page_ok"] and scored["late_penalty"]["quote_ok"]  # heading prefix is fine
    assert scored["volume_discount"]["status"] == "correct"  # 5.0 equals 5
    assert scored["payment_terms"]["status"] == "correct_absent"
    assert scored["unit_price"]["status"] == "correct_absent"


def test_a_wrong_value_is_reported_field_by_field():
    scored = score_case(SPEC, result([late(percent="12"), volume()]), GOLD_SOURCES)
    entry = scored["late_penalty"]
    assert entry["status"] == "wrong"
    assert entry["fields"]["percent"] is False and entry["fields"]["deadline"] is True


def test_missing_rule_is_refused_when_an_issue_exists_and_silent_otherwise():
    issues = [ExtractionIssue(clause_type="late_penalty", reason="Quote not found in the contract text")]
    scored = score_case(SPEC, result([], issues), GOLD_SOURCES)
    assert scored["late_penalty"]["status"] == "refused"
    assert scored["volume_discount"]["status"] == "silent_miss"


def test_rule_that_is_not_in_the_answer_key_is_spurious():
    extra = UnitPriceRule(item_name="Server", agreed_unit_price=Decimal(100), source=Source(page=2, text=VOL_Q))
    scored = score_case(SPEC, result([late(), volume(), extra]), GOLD_SOURCES)
    assert scored["unit_price"]["status"] == "spurious"


def test_wrong_page_does_not_make_the_values_wrong():
    scored = score_case(SPEC, result([late(page=5), volume()]), GOLD_SOURCES)
    assert scored["late_penalty"]["status"] == "correct" and scored["late_penalty"]["page_ok"] is False


def test_aggregate_counts_recall_and_precision():
    perfect = score_case(SPEC, result([late(), volume()]), GOLD_SOURCES)
    wrong = score_case(SPEC, result([late(percent="12")]), GOLD_SOURCES)
    summary = aggregate([perfect, wrong])
    assert summary["late_penalty"]["recall"] == 0.5 and summary["late_penalty"]["precision"] == 0.5
    assert summary["volume_discount"]["recall"] == 0.5
    assert summary["volume_discount"]["silent_miss"] == 1
    assert summary["ALL"]["gold"] == 4 and summary["ALL"]["correct"] == 2
    assert summary["late_penalty"]["field_accuracy"] == 0.9  # 9 of 10 fields right


def test_without_gold_sources_values_are_scored_but_page_and_quote_are_not():
    scored = score_case(SPEC, result([late(), volume()]), {})
    assert scored["late_penalty"]["status"] == "correct"
    assert scored["late_penalty"]["page_ok"] is None and scored["late_penalty"]["quote_ok"] is None
    summary = aggregate([scored])
    assert summary["ALL"]["recall"] == 1.0 and summary["ALL"]["field_accuracy"] == 1.0
    assert summary["ALL"]["page_accuracy"] is None and summary["ALL"]["quote_accuracy"] is None