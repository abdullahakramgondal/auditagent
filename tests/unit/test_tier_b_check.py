from data.tier_b.check_contract import review_text

SPEC = {
    "rules": [
        {"clause_type": "late_penalty", "deadline": "2026-11-20", "mode": "flat_percent", "percent": "8", "grace_days": 5},
        {"clause_type": "payment_terms", "net_days": 45},
    ]
}

CLEAN = [
    "1. Parties This Agreement is made on 1 October 2026.\n"
    "4.2 Delay. If the Vendor delivers after 20 November 2026, a penalty of eight percent (8%) of the invoice applies, "
    "but the first five (5) days of delay carry no penalty.",
    "7. Payment. Each invoice shall be paid within forty-five (45) days of the invoice date.\n"
    "9. Liability. Liability is capped at 10% of the order value. Termination needs thirty (30) days notice. "
    "A late payment charge of 2% per month applies if the Buyer pays late.",
]


def test_clean_contract_has_every_value_and_nothing_extra():
    report = review_text(SPEC, CLEAN)
    assert all(page for _, page in report["required"])
    assert report["unexpected"] == []


def test_missing_required_value_is_reported():
    pages = [CLEAN[0].replace("20 November 2026", "21 November 2026"), CLEAN[1]]
    missing = [label for label, page in review_text(SPEC, pages)["required"] if page is None]
    assert missing == ["late_penalty deadline 2026-11-20"]


def test_extra_rule_numbers_are_flagged_with_page_and_context():
    pages = [CLEAN[0], CLEAN[1] + " A handling fee of 3% applies. Payment within 90 days is also accepted."]
    unexpected = review_text(SPEC, pages)["unexpected"]
    assert {(p, k, v) for p, k, v, _ in unexpected} == {(2, "percent", "3"), (2, "days", "90")}
    assert "handling fee" in unexpected[0][3]


def test_numbers_written_only_as_words_are_listed():
    pages = ["A penalty of ten percent applies and payment is due within thirty days.", CLEAN[1]]
    phrases = [p.lower() for _, p, _ in review_text(SPEC, pages)["number_words"]]
    assert phrases == ["ten percent", "thirty days"]


def test_words_followed_by_digits_in_brackets_are_not_flagged():
    pages = ["a penalty of eight percent (8%) applies", CLEAN[1]]
    assert review_text(SPEC, pages)["number_words"] == []


def test_words_ending_in_rs_do_not_look_like_rupee_amounts():
    """Regression: 'Vendors,' once matched as 'Rs' followed by a comma and crashed the checker."""
    pages = ["The Vendors, Buyers, partners, and offers, all agree.", CLEAN[0], CLEAN[1]]
    report = review_text(SPEC, pages)
    assert report["unexpected"] == []


def test_real_amounts_are_read_with_or_without_trailing_comma():
    spec = {"rules": [{"clause_type": "unit_price", "item_name": "Cisco Catalyst 9300 Switch", "agreed_unit_price": "540000"}]}
    pages = ["The price of the Cisco Catalyst 9300 Switch is PKR 540,000, per unit. A fee of Rs. 5,000 applies."]
    unexpected = review_text(spec, pages)["unexpected"]
    assert [(k, v) for _, k, v, _ in unexpected] == [("amounts", "5,000")]


def test_volume_discount_written_with_the_number_in_brackets_is_found():
    spec = {"rules": [{"clause_type": "volume_discount", "min_quantity": 40, "discount_percent": "6"}]}
    pages = ["An order of forty (40) or more units receives a discount of six percent (6%)."]
    report = review_text(spec, pages)
    assert all(page for _, page in report["required"])
    assert report["unexpected"] == []