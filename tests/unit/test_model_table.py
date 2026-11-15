"""model_table compares models rule by rule from saved results."""

from datetime import date
from decimal import Decimal

from auditagent.schemas.contract import (
    ExtractedContract,
    LatePenaltyRule,
    PaymentTermsRule,
    Source,
)
from auditagent.schemas.extraction import AgentOneResult, ExtractionIssue
from eval.model_table import compare

SOURCE = Source(page=1, text="The clause text.")
LATE_SPEC = {
    "clause_type": "late_penalty",
    "deadline": "2026-10-15",
    "mode": "flat_percent",
    "percent": "10",
    "grace_days": 0,
}
TERMS_SPEC = {"clause_type": "payment_terms", "net_days": 30}


def spec(case_id):
    return {"case_id": case_id, "rules": [LATE_SPEC, TERMS_SPEC]}


def late(percent="10"):
    return LatePenaltyRule(
        deadline=date(2026, 10, 15),
        mode="flat_percent",
        percent=Decimal(percent),
        grace_days=0,
        source=SOURCE,
    )


def terms():
    return PaymentTermsRule(net_days=30, source=SOURCE)


def result(rules, issues=()):
    contract = ExtractedContract(rules=list(rules))
    return AgentOneResult(contract=contract, issues=list(issues), llm_model="m")


REFUSED_LATE = [ExtractionIssue(clause_type="late_penalty", reason="Quote not found")]
BOTH = (result([late(), terms()]), {})
ONLY_TERMS = (result([terms()], REFUSED_LATE), {})
NOTHING = (result([], REFUSED_LATE), {})


def test_each_model_is_counted_and_the_second_adds_what_the_first_missed():
    runs = {"a": {"tb_x": ONLY_TERMS}, "b": {"tb_x": BOTH}}
    report = compare({"tb_x": spec("tb_x")}, runs)
    assert report["rules"] == 2 and report["contracts"] == 1
    assert report["per_model"]["a"] == {"correct": 1, "wrong": 0, "refused": 1, "silent_miss": 0}
    assert report["per_model"]["b"]["correct"] == 2
    assert report["cumulative"] == [("a", 1), ("b", 2)]
    assert report["missed_by_all"] == []


def test_a_rule_that_every_model_misses_is_listed_as_a_weakness_of_the_pipeline():
    runs = {"a": {"tb_x": ONLY_TERMS}, "b": {"tb_x": ONLY_TERMS}}
    report = compare({"tb_x": spec("tb_x")}, runs)
    assert report["missed_by_all"] == [("tb_x", "late_penalty")]


def test_a_wrong_value_is_reported_with_its_model():
    wrong_value = (result([late("12"), terms()]), {})
    runs = {"a": {"tb_x": BOTH}, "b": {"tb_x": wrong_value}}
    report = compare({"tb_x": spec("tb_x")}, runs)
    assert report["wrong"] == [("tb_x", "late_penalty", "b")]
    assert report["cumulative"][-1] == ("b", 2)  # the right answer of model a still counts


def test_only_contracts_that_every_model_has_run_are_compared():
    runs = {"a": {"tb_x": BOTH, "tb_y": BOTH}, "b": {"tb_x": NOTHING}}
    specs = {"tb_x": spec("tb_x"), "tb_y": spec("tb_y")}
    report = compare(specs, runs)
    assert report["contracts"] == 1 and report["rules"] == 2
