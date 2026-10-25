import json
from collections import Counter
from decimal import Decimal

from auditagent.schemas.contract import ExtractedContract
from auditagent.schemas.invoice import InvoiceData, PurchaseOrderData
from data.generator.build_case import build_case
from data.generator.spec_generator import CATEGORY_PLAN, SPEC_DIR, generate_all

COMPLIANT = {"compliant_plain", "compliant_applied", "grace_inside"}
SINGLE_FINDING = {
    "late_flat": ["late_penalty"],
    "late_per_day": ["late_penalty"],
    "decoy": ["late_penalty"],
    "volume_missed": ["volume_discount"],
    "price_over": ["unit_price"],
    "terms_wrong": ["payment_terms"],
}


def test_thirty_specs_with_unique_ids_and_planned_categories():
    specs = generate_all()
    assert len(specs) == 30
    assert len({s["case_id"] for s in specs}) == 30
    assert Counter(s["category"] for s in specs) == dict(CATEGORY_PLAN)


def test_generation_is_deterministic():
    assert generate_all() == generate_all()


def test_specs_validate_against_schemas():
    for spec in generate_all():
        rules = [{**r, "source": {"page": 1, "text": "placeholder"}} for r in spec["rules"]]
        ExtractedContract.model_validate({"rules": rules})
        PurchaseOrderData.model_validate(spec["purchase_order"])
        InvoiceData.model_validate(spec["invoice"])


def test_expected_is_internally_consistent():
    for s in generate_all():
        e = s["expected"]
        diff = Decimal(e["billed_total"]) - Decimal(e["correct_payable"])
        assert diff == Decimal(e["total_difference"]), s["case_id"]
        total = sum(Decimal(v) for v in e["finding_amounts"].values())
        assert total == Decimal(e["total_difference"]), s["case_id"]


def test_applied_deductions_are_visible_on_invoice():
    applied_specs = [s for s in generate_all() if s["vendor_applied"]]
    assert len(applied_specs) == 2
    for s in applied_specs:
        assert len(s["invoice"]["adjustments"]) == len(s["vendor_applied"])
        assert all(Decimal(a["amount"]) < 0 for a in s["invoice"]["adjustments"])


def test_category_outcomes_match_the_intent():
    for s in generate_all():
        e, cat = s["expected"], s["category"]
        if cat in COMPLIANT:
            assert e["status"] == "COMPLIANT", s["case_id"]
            assert e["finding_types"] == [], s["case_id"]
        else:
            assert e["status"] == "NON_COMPLIANT", s["case_id"]
        if cat in SINGLE_FINDING:
            assert e["finding_types"] == SINGLE_FINDING[cat], s["case_id"]
        if cat == "multi_breach":
            assert set(e["finding_types"]) == {r["clause_type"] for r in s["rules"]}, s["case_id"]


def test_layout_ranges_and_variety():
    specs = generate_all()
    for s in specs:
        pages = s["layout"]["contract_pages"]
        assert 3 <= pages <= 20
        assert all(2 <= p <= pages for p in s["layout"]["target_page"].values())
    assert {s["layout"]["wording_variant"] for s in specs} == {1, 2, 3}
    assert max(s["layout"]["contract_pages"] for s in specs) >= 12


def test_specs_on_disk_match_generator():
    for spec in generate_all():
        path = SPEC_DIR / f"{spec['case_id']}.json"
        assert path.exists(), f"missing {path.name}: run python -m data.generator.spec_generator"
        assert json.loads(path.read_text()) == json.loads(json.dumps(spec))


def test_all_specs_build_into_pdfs(tmp_path):
    for spec in generate_all():
        spec_path = tmp_path / f"{spec['case_id']}.json"
        spec_path.write_text(json.dumps(spec))
        out = build_case(spec_path, tmp_path / "out")
        expected = json.loads((out / "expected.json").read_text())
        for kind, target in spec["layout"]["target_page"].items():
            assert expected["rule_sources"][kind]["page"] == target, spec["case_id"]


def test_all_three_document_layouts_are_used():
    specs = generate_all()
    assert {s["layout"]["doc_variant"] for s in specs} == {1, 2, 3}
