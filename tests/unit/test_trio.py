"""The matched trio of a Tier B contract: its answer key and its documents are right."""

from decimal import Decimal

from auditagent.schemas.invoice import InvoiceData, PurchaseOrderData
from data.tier_b.make_prompts import SPECS
from data.trio.make_trio import build_trio


def spec_named(case_id):
    return next(spec for spec in SPECS if spec["case_id"] == case_id)


def test_tb_04_with_every_rule_broken_has_the_hand_checked_answer():
    """120 laptops at the agreed 275,000 = 33,000,000; the invoice charges 288,750 each."""
    expected = build_trio(spec_named("tb_04"))["expected"]
    assert expected["status"] == "NON_COMPLIANT"
    assert expected["billed_total"] == Decimal(34650000)
    assert expected["correct_payable"] == Decimal(25740000)  # 33,000,000 - 3,960,000 - 3,300,000
    assert expected["total_difference"] == Decimal(8910000)
    assert expected["finding_types"] == [
        "late_penalty",
        "payment_terms",
        "unit_price",
        "volume_discount",
    ]
    assert expected["finding_amounts"]["late_penalty"] == Decimal(3300000)
    assert expected["finding_amounts"]["volume_discount"] == Decimal(3960000)
    assert expected["finding_amounts"]["unit_price"] == Decimal(1650000)


def test_tb_04_clean_invoice_follows_the_contract():
    expected = build_trio(spec_named("tb_04"), clean=True)["expected"]
    assert expected["status"] == "COMPLIANT" and expected["finding_types"] == []
    assert expected["billed_total"] == expected["correct_payable"] == Decimal(27225000)


def test_every_tier_b_contract_gets_a_valid_trio_in_both_scenarios():
    for spec in SPECS:
        kinds = sorted({rule["clause_type"] for rule in spec["rules"]})
        breach = build_trio(spec)
        assert breach["expected"]["status"] == "NON_COMPLIANT", spec["case_id"]
        assert breach["expected"]["finding_types"] == kinds, spec["case_id"]
        clean = build_trio(spec, clean=True)
        assert clean["expected"]["status"] == "COMPLIANT", spec["case_id"]
        for trio in (breach, clean):
            InvoiceData.model_validate(trio["invoice"])
            PurchaseOrderData.model_validate(trio["purchase_order"])
            gap = trio["expected"]["billed_total"] - trio["expected"]["correct_payable"]
            assert gap == trio["expected"]["total_difference"], spec["case_id"]
