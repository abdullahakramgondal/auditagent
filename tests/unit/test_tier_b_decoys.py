"""Tests for the optional style_notes, extra_decoys and decoy_numbers of a Tier B spec."""

from auditagent.agents.grounding import DAYS_RE, PERCENT_RE
from data.tier_b.check_contract import DECOY_DAYS, DECOY_PERCENTS, review_text
from data.tier_b.make_prompts import SPECS, build_prompt


def test_the_prompt_carries_the_style_notes_and_the_extra_decoys():
    for spec in SPECS:
        prompt = build_prompt(spec)
        for decoy in spec.get("extra_decoys", []):
            assert decoy in prompt, spec["case_id"]
        for note in spec.get("style_notes", []):
            assert note in prompt, spec["case_id"]


def test_a_spec_without_style_notes_gets_no_notes_section():
    prompt = build_prompt(SPECS[0])
    assert "How to write these terms" not in prompt
    assert "Everything else" in prompt


def test_every_number_in_an_extra_decoy_is_declared_for_the_checker():
    """Otherwise check_contract would report a harmless decoy as an unexpected rule."""
    for spec in SPECS:
        declared = spec.get("decoy_numbers", {})
        for decoy in spec.get("extra_decoys", []):
            for kind, pattern in (("percent", PERCENT_RE), ("days", DAYS_RE)):
                for match in pattern.finditer(decoy):
                    token = next(g for g in match.groups() if g)
                    assert float(token) in declared.get(kind, []), (spec["case_id"], kind, token)


def test_declared_decoy_numbers_are_not_reported_as_unexpected():
    spec = {
        "rules": [{"clause_type": "payment_terms", "net_days": 45}],
        "decoy_numbers": {"percent": [1.5], "days": [7]},
    }
    pages = [
        ("Each invoice shall be paid within forty-five (45) days of the invoice date. "
        "A discount of 1.5% applies to an invoice paid within seven (7) days.")
    ]
    assert review_text(spec, pages)["unexpected"] == []
    undeclared = {"rules": spec["rules"]}
    kinds = {kind for _, kind, _, _ in review_text(undeclared, pages)["unexpected"]}
    assert kinds == {"percent", "days"}


def test_the_untouched_specs_use_rule_values_that_no_decoy_shares():
    """tb_09 to tb_12: a rule value equal to a decoy value could not be told apart by check_contract."""
    for spec in SPECS[8:]:
        declared = spec.get("decoy_numbers", {})
        decoy_percent = DECOY_PERCENTS | {float(v) for v in declared.get("percent", [])}
        decoy_days = DECOY_DAYS | {float(v) for v in declared.get("days", [])}
        for rule in spec["rules"]:
            percents = [rule.get("percent"), rule.get("cap_percent"), rule.get("discount_percent")]
            days = [rule.get("grace_days"), rule.get("net_days")]
            assert not {float(v) for v in percents if v} & decoy_percent, spec["case_id"]
            assert not {float(v) for v in days if v} & decoy_days, spec["case_id"]
