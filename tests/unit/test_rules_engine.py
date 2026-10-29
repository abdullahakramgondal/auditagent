"""The rule engine must give the answer key of every generated case, and the edge cases by hand."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from auditagent.rules.engine import audit_invoice, late_penalty_percent, same_item
from auditagent.schemas.audit import AuditResult
from auditagent.schemas.contract import (
    ExtractedContract,
    LatePenaltyRule,
    PaymentTermsRule,
    Source,
    UnitPriceRule,
    VolumeDiscountRule,
)
from auditagent.schemas.invoice import InvoiceData

SPEC_DIR = Path(__file__).resolve().parents[2] / "data" / "specs"
SOURCE = Source(page=4, text="The clause text.")


def late(**changes):
    fields = {
        "deadline": date(2026, 10, 15),
        "mode": "flat_percent",
        "percent": Decimal(10),
        "grace_days": 0,
        "source": SOURCE,
    }
    return LatePenaltyRule(**{**fields, **changes})


def volume(min_quantity=50, percent=5):
    return VolumeDiscountRule(
        min_quantity=min_quantity, discount_percent=Decimal(percent), source=SOURCE
    )


def price(item="Server", agreed=1000000):
    return UnitPriceRule(item_name=item, agreed_unit_price=Decimal(agreed), source=SOURCE)


def terms(days=30):
    return PaymentTermsRule(net_days=days, source=SOURCE)


def contract(*rules):
    return ExtractedContract(rules=list(rules))


def invoice(
    quantity=10,
    unit_price=1000000,
    delivered=date(2026, 10, 25),
    due=None,
    adjustments=(),
    total=None,
    name="Server",
):
    rows = quantity * unit_price
    adjusted = rows + sum(int(a["amount"]) for a in adjustments)
    return InvoiceData.model_validate(
        {
            "invoice_number": "INV-1",
            "invoice_date": "2026-10-26",
            "delivery_date": None if delivered is None else delivered.isoformat(),
            "due_date": None if due is None else due.isoformat(),
            "line_items": [
                {
                    "item_name": name,
                    "quantity": quantity,
                    "unit_price": str(unit_price),
                    "line_total": str(rows),
                }
            ],
            "adjustments": list(adjustments),
            "total_amount": str(total if total is not None else adjusted),
        }
    )


def types(result):
    return [finding.clause_type for finding in result.findings]


# ---- the answer key of the generated dataset (no model involved) ----


@pytest.mark.parametrize("path", sorted(SPEC_DIR.glob("*.json")), ids=lambda p: p.stem)
def test_the_engine_gives_the_answer_key_of_every_generated_case(path):
    spec = json.loads(path.read_text())
    expected = spec["expected"]
    rules = [{**r, "source": {"page": 1, "text": "placeholder"}} for r in spec["rules"]]
    result = audit_invoice(
        ExtractedContract.model_validate({"rules": rules}),
        InvoiceData.model_validate(spec["invoice"]),
    )
    assert result.status == expected["status"]
    assert result.billed_total == Decimal(expected["billed_total"])
    assert result.correct_payable == Decimal(expected["correct_payable"])
    assert result.total_difference == Decimal(expected["total_difference"])
    assert sorted(types(result)) == expected["finding_types"]
    assert result.review_reasons == []
    amounts = expected.get("finding_amounts")
    if amounts:
        got = {finding.clause_type: finding.difference for finding in result.findings}
        assert got == {kind: Decimal(value) for kind, value in amounts.items()}


# ---- the late penalty ----


def test_a_flat_penalty_for_a_late_delivery():
    result = audit_invoice(contract(late()), invoice())
    assert result.status == "NON_COMPLIANT" and types(result) == ["late_penalty"]
    assert result.billed_total == Decimal(10000000)
    assert result.correct_payable == Decimal(9000000)
    assert result.total_difference == Decimal(1000000)
    finding = result.findings[0]
    assert finding.source.page == 4
    assert finding.expected_amount == Decimal(9000000) and finding.billed_amount == Decimal(
        10000000
    )


def test_no_penalty_when_the_delivery_is_on_time():
    result = audit_invoice(contract(late()), invoice(delivered=date(2026, 10, 15)))
    assert result.status == "COMPLIANT" and result.total_difference == 0


def test_a_flat_penalty_needs_more_days_than_the_grace_period():
    rule = late(grace_days=3)
    assert late_penalty_percent(rule, date(2026, 10, 18)) == 0
    assert late_penalty_percent(rule, date(2026, 10, 19)) == 10
    assert (
        audit_invoice(contract(rule), invoice(delivered=date(2026, 10, 17))).status == "COMPLIANT"
    )


def test_a_per_day_penalty_counts_only_the_days_after_the_grace_period():
    rule = late(mode="per_day_percent", percent=Decimal(1), cap_percent=Decimal(10), grace_days=3)
    assert late_penalty_percent(rule, date(2026, 10, 20)) == 2  # 5 days late, 3 are free


def test_a_per_day_penalty_stops_at_its_cap():
    rule = late(mode="per_day_percent", percent=Decimal(1), cap_percent=Decimal(10))
    result = audit_invoice(contract(rule), invoice(delivered=date(2026, 10, 30)))
    assert result.total_difference == Decimal(1000000)  # 15 days would be 15%, the cap says 10%


def test_a_late_rule_without_a_delivery_date_needs_review():
    result = audit_invoice(contract(late()), invoice(delivered=None))
    assert result.status == "NEEDS_REVIEW"
    assert "delivery date" in result.review_reasons[0]


# ---- the volume discount ----


def test_a_missed_volume_discount():
    result = audit_invoice(contract(volume()), invoice(quantity=60))
    assert types(result) == ["volume_discount"]
    assert result.total_difference == Decimal(3000000)
    assert result.correct_payable == Decimal(57000000)


def test_no_volume_discount_below_the_minimum():
    assert audit_invoice(contract(volume()), invoice(quantity=49)).status == "COMPLIANT"


# ---- the agreed unit price ----


def test_an_overcharge_above_the_agreed_unit_price():
    result = audit_invoice(contract(price()), invoice(unit_price=1100000))
    assert types(result) == ["unit_price"]
    assert result.billed_total == Decimal(11000000)
    assert result.correct_payable == Decimal(10000000)
    assert result.total_difference == Decimal(1000000)
    assert result.findings[0].expected_amount == Decimal(10000000)


def test_a_price_below_the_agreed_price_is_not_a_finding():
    assert audit_invoice(contract(price()), invoice(unit_price=900000)).status == "COMPLIANT"


def test_items_are_matched_by_containment_not_equality():
    assert same_item("Leased Line 100 Mbps", "Leased Line 100 Mbps (annual)")
    assert same_item("  server ", "Server")
    assert not same_item("Router", "Server")
    rule = price(item="Leased Line 100 Mbps")
    result = audit_invoice(
        contract(rule), invoice(unit_price=1100000, name="Leased Line 100 Mbps (annual)")
    )
    assert types(result) == ["unit_price"]


# ---- the payment terms ----


def test_a_due_date_earlier_than_the_terms_allow_is_a_finding_without_money():
    result = audit_invoice(contract(terms()), invoice(due=date(2026, 11, 10)))
    assert result.status == "NON_COMPLIANT" and types(result) == ["payment_terms"]
    assert result.total_difference == 0


def test_a_due_date_that_meets_the_terms_is_compliant():
    assert audit_invoice(contract(terms()), invoice(due=date(2026, 11, 25))).status == "COMPLIANT"


def test_payment_terms_without_a_due_date_need_review_and_no_date_is_computed():
    result = audit_invoice(contract(terms()), invoice(due=None))
    assert result.status == "NEEDS_REVIEW" and "due date" in result.review_reasons[0]


# ---- what the vendor already deducted ----


def test_a_penalty_that_the_vendor_applied_is_not_a_finding():
    deduction = [{"label": "Less: late delivery penalty", "amount": "-1000000"}]
    result = audit_invoice(contract(late()), invoice(adjustments=deduction))
    assert result.status == "COMPLIANT"
    assert result.billed_total == Decimal(9000000) == result.correct_payable


def test_a_partly_applied_penalty_leaves_the_rest_as_a_finding():
    deduction = [{"label": "Less: late delivery penalty", "amount": "-400000"}]
    result = audit_invoice(contract(late()), invoice(adjustments=deduction))
    assert types(result) == ["late_penalty"]
    assert result.total_difference == Decimal(600000)


def test_an_adjustment_that_no_rule_explains_needs_review():
    tax = [{"label": "Sales Tax (18%)", "amount": "1800000"}]
    result = audit_invoice(contract(), invoice(adjustments=tax))
    assert result.status == "NEEDS_REVIEW"
    assert any("Sales Tax" in reason for reason in result.review_reasons)


# ---- review reasons from the agents ----


def test_issues_of_the_agents_make_a_clean_audit_need_review():
    result = audit_invoice(contract(), invoice(), extra_review_reasons=["a rule was refused"])
    assert result.status == "NEEDS_REVIEW" and result.review_reasons == ["a rule was refused"]


def test_review_reasons_stay_next_to_a_proven_finding():
    result = audit_invoice(contract(late()), invoice(), extra_review_reasons=["a rule was refused"])
    assert result.status == "NON_COMPLIANT" and result.review_reasons == ["a rule was refused"]


# ---- the checks of the schema (TODO item 1) ----

RESULT = {
    "status": "NON_COMPLIANT",
    "billed_total": "10000000",
    "correct_payable": "9000000",
    "total_difference": "1000000",
    "findings": [
        {
            "clause_type": "late_penalty",
            "description": "Late.",
            "source": {"page": 4, "text": "Clause."},
            "difference": "1000000",
        }
    ],
}


def test_a_total_that_is_not_the_sum_of_the_findings_is_rejected():
    with pytest.raises(ValidationError):
        AuditResult.model_validate({**RESULT, "total_difference": "2000000"})


def test_billed_minus_correct_must_equal_the_total_unless_a_reason_explains_it():
    off = {**RESULT, "correct_payable": "8000000"}
    with pytest.raises(ValidationError):
        AuditResult.model_validate(off)
    assert AuditResult.model_validate({**off, "review_reasons": ["not explained"]})
