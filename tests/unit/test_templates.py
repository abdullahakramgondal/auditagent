import pytest

from data.generator.templates import VARIANTS, build_contract_sections, render_clause

LATE_FLAT = {
    "clause_type": "late_penalty",
    "deadline": "2026-10-15",
    "mode": "flat_percent",
    "percent": "10",
    "grace_days": 0,
}

CASES = [
    (LATE_FLAT, ["15 October 2026", "10%"]),
    (
        {
            "clause_type": "late_penalty",
            "deadline": "2026-10-15",
            "mode": "per_day_percent",
            "percent": "1",
            "cap_percent": "10",
            "grace_days": 3,
        },
        ["15 October 2026", "1%", "10%", "3 days"],
    ),
    ({"clause_type": "volume_discount", "min_quantity": 50, "discount_percent": "5"}, ["50", "5%"]),
    ({"clause_type": "payment_terms", "net_days": 30}, ["30"]),
    (
        {"clause_type": "unit_price", "item_name": "Server", "agreed_unit_price": "1000000"},
        ["Server", "PKR 1,000,000"],
    ),
]


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("rule,must_contain", CASES)
def test_clause_text_contains_its_numbers(rule, must_contain, variant):
    text = render_clause(rule, variant)
    for piece in must_contain:
        assert piece in text


def test_sections_are_deterministic_and_keep_decoys():
    spec = {
        "seed": 1,
        "buyer": "Buyer Co",
        "vendor": "Vendor Co",
        "layout": {"wording_variant": 1, "filler_clauses": ["liability", "confidentiality"]},
        "rules": [LATE_FLAT],
    }
    first = build_contract_sections(spec)
    second = build_contract_sections(spec)
    assert first == second

    keys = [s["key"] for s in first]
    assert "late_penalty" in keys and "liability" in keys
    liability = next(s for s in first if s["key"] == "liability")
    assert "10%" in liability["text"]