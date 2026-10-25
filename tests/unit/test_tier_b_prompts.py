from auditagent.schemas.contract import ExtractedContract
from data.tier_b.make_prompts import DECOYS, SPECS, build_prompt, describe_rule


def test_specs_are_valid_rules_with_unique_ids():
    ids = [s["case_id"] for s in SPECS]
    assert len(set(ids)) == len(ids) == 8
    for spec in SPECS:
        rules = [{**r, "source": {"page": 1, "text": "placeholder"}} for r in spec["rules"]]
        ExtractedContract.model_validate({"rules": rules})


def test_every_clause_type_and_both_writers_are_covered():
    kinds = {r["clause_type"] for s in SPECS for r in s["rules"]}
    assert kinds == {"late_penalty", "volume_discount", "payment_terms", "unit_price"}
    assert {s["writer"] for s in SPECS} == {"claude", "chatgpt"}
    modes = {r["mode"] for s in SPECS for r in s["rules"] if r["clause_type"] == "late_penalty"}
    assert modes == {"flat_percent", "per_day_percent"}


def test_prompt_states_every_value_and_every_decoy():
    for spec in SPECS:
        prompt = build_prompt(spec)
        for rule in spec["rules"]:
            assert describe_rule(rule) in prompt
        for decoy in DECOYS:
            assert decoy in prompt
        assert spec["buyer"] in prompt and spec["vendor"] in prompt


def test_rule_descriptions_carry_the_exact_numbers():
    late = next(r for r in SPECS[1]["rules"] if r["clause_type"] == "late_penalty")
    text = describe_rule(late)
    assert "5 December 2026" in text and "1.5%" in text and "12%" in text
    price = next(r for r in SPECS[2]["rules"] if r["clause_type"] == "unit_price")
    assert "PKR 540,000" in describe_rule(price)
