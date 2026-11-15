"""The purchase order prompt says that the Buyer issues the order (a purchase order goes to the Vendor)."""

from data.tier_b.make_prompts import SPECS
from data.trio.make_trio import build_trio, make_prompt


def spec_named(case_id):
    return next(spec for spec in SPECS if spec["case_id"] == case_id)


def test_a_purchase_order_is_written_from_the_buyer_to_the_vendor():
    spec = spec_named("tb_08")
    prompt = make_prompt(spec, build_trio(spec), "purchase_order")
    assert f'from {spec["buyer"]} (the "Buyer") to {spec["vendor"]} (the "Vendor")' in prompt
    assert f'from {spec["vendor"]} (the "Vendor") to' not in prompt


def test_an_invoice_is_still_written_from_the_vendor_to_the_buyer():
    spec = spec_named("tb_08")
    prompt = make_prompt(spec, build_trio(spec), "invoice")
    assert f'from {spec["vendor"]} (the "Vendor") to {spec["buyer"]} (the "Buyer")' in prompt


def test_every_tier_b_contract_gets_both_prompts_with_all_its_values():
    for spec in SPECS:
        trio = build_trio(spec)
        for key, total in (("purchase_order", "total_amount"), ("invoice", "total_amount")):
            prompt = make_prompt(spec, trio, key)
            assert f"{int(trio[key][total]):,}" in prompt, spec["case_id"]
