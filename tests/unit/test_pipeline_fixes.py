"""The pipeline fixes of Day 29: a date followed by its defined term, and a rule found twice."""

import json
from datetime import date
from decimal import Decimal

from auditagent.agents.grounding import parse_written_date
from auditagent.agents.legal_extractor import LegalExtractor, merge_rules
from auditagent.ingestion.embedder import HashingEmbedder
from auditagent.llm.fake import ScriptedProvider
from auditagent.schemas.contract import Source, UnitPriceRule, VolumeDiscountRule
from auditagent.schemas.document import PageText, ParsedDocument

LATE_Q = (
    "If delivery of the goods is later than 15 October 2026, "
    "a penalty of 10% shall apply to the final invoice."
)
PAYMENT_Q = "All invoices are payable 30 calendar days after the date of invoice."
SPARE_Q = "Invoices for spare parts are payable 45 days after the date of invoice."
EMPTY = json.dumps({"rules": []})


def doc(pages):
    return ParsedDocument(
        source_name="c.pdf",
        sha256="b" * 64,
        pages=[PageText(number=i, text=t) for i, t in enumerate(pages, start=1)],
    )


def source(text="The clause text."):
    return Source(page=1, text=text)


# ---- a date followed by its defined term ----


def test_a_defined_term_after_the_date_is_ignored():
    straight = '28 February 2027 (the "Delivery Deadline")'
    curly = "28 February 2027 (the \u201cDelivery Deadline\u201d)"
    assert parse_written_date(straight) == date(2027, 2, 28)
    assert parse_written_date(curly) == date(2027, 2, 28)
    assert parse_written_date("2026-10-15 (the Delivery Date)") == date(2026, 10, 15)


def test_other_text_around_a_date_is_still_not_a_date():
    assert parse_written_date("28 February 2027 and later") is None
    assert parse_written_date('(the "Delivery Deadline") 28 February 2027') is None
    assert parse_written_date("(the Delivery Deadline)") is None


def late_rule(deadline):
    return {
        "quote": LATE_Q,
        "chunk_id": "b-002",
        "deadline_quote": LATE_Q,
        "deadline": deadline,
        "mode": "flat_percent",
        "percent": 10,
        "cap_percent": None,
        "grace_days": 0,
    }


def extract_late(deadline):
    pages = [
        "SUPPLY AGREEMENT\n1. Parties\nThis Agreement is between Buyer Co and Vendor Co.\nPage 1 of 2",
        f"SUPPLY AGREEMENT\n3. Late Delivery\n{LATE_Q}\nPage 2 of 2",
    ]
    replies = [json.dumps({"rules": [late_rule(deadline)]}), EMPTY, EMPTY, EMPTY]
    return LegalExtractor(ScriptedProvider(replies), HashingEmbedder()).extract(doc(pages))


def test_a_deadline_with_its_defined_term_is_accepted_when_the_date_is_in_the_quote():
    result = extract_late("15 October 2026 (the \u201cDelivery Deadline\u201d)")
    assert result.issues == []
    assert result.contract.rules[0].deadline == date(2026, 10, 15)


def test_a_deadline_with_its_defined_term_is_still_refused_when_the_date_is_not_written():
    result = extract_late('16 October 2026 (the "Delivery Deadline")')
    assert result.contract.rules == []
    issue = next(i for i in result.issues if i.clause_type == "late_penalty")
    assert "not written in the quote" in issue.reason


# ---- the same rule twice ----


def volume(percent, first_page_text="Clause A."):
    return VolumeDiscountRule(
        min_quantity=25, discount_percent=Decimal(percent), source=source(first_page_text)
    )


def price(item, amount, text="Clause."):
    return UnitPriceRule(item_name=item, agreed_unit_price=Decimal(amount), source=source(text))


def test_the_same_rule_with_another_spelling_of_the_number_is_kept_once():
    rules, issues = merge_rules(
        "volume_discount", [volume("5", "First."), volume("5.0", "Second.")]
    )
    assert len(rules) == 1 and issues == []
    assert rules[0].source.text == "First."


def test_two_different_rules_for_the_same_thing_are_dropped_and_sent_to_review():
    rules, issues = merge_rules("volume_discount", [volume("5"), volume("6")])
    assert rules == [] and len(issues) == 1
    assert issues[0].clause_type == "volume_discount" and "different" in issues[0].reason


def test_unit_prices_of_different_items_are_all_kept():
    rules, issues = merge_rules("unit_price", [price("Server", 100), price("Router", 50)])
    assert len(rules) == 2 and issues == []


def test_two_prices_for_one_item_are_dropped_but_another_item_is_kept():
    found = [price("Server", 100), price("server", 120), price("Router", 50)]
    rules, issues = merge_rules("unit_price", found)
    assert [r.item_name for r in rules] == ["Router"]
    assert len(issues) == 1 and "server" in issues[0].reason


PAGES = [
    "SUPPLY AGREEMENT\n1. Parties\nThis Agreement is between Buyer Co and Vendor Co.\nPage 1 of 2",
    f"SUPPLY AGREEMENT\n5. Payment Terms\n{PAYMENT_Q}\n6. Spare Parts\n{SPARE_Q}\nPage 2 of 2",
]


def payment(quote, days):
    return {"quote": quote, "chunk_id": "x-001", "net_days": days}


def extract_payment(*rules):
    replies = [EMPTY, EMPTY, json.dumps({"rules": list(rules)}), EMPTY]
    return LegalExtractor(ScriptedProvider(replies), HashingEmbedder()).extract(doc(PAGES))


def test_a_model_that_returns_the_payment_rule_twice_gives_one_rule():
    result = extract_payment(payment(PAYMENT_Q, 30), payment(PAYMENT_Q, 30))
    assert result.issues == []
    assert [r.net_days for r in result.contract.rules] == [30]


def test_two_proven_but_different_payment_rules_go_to_review():
    result = extract_payment(payment(PAYMENT_Q, 30), payment(SPARE_Q, 45))
    assert result.contract.rules == []
    issue = next(i for i in result.issues if i.clause_type == "payment_terms")
    assert "different" in issue.reason
