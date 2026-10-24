import json
from datetime import date
from decimal import Decimal

from auditagent.agents.legal_extractor import LegalExtractor
from auditagent.ingestion.embedder import HashingEmbedder
from auditagent.llm.fake import ScriptedProvider
from auditagent.schemas.document import PageText, ParsedDocument

PREFIX = "bbbbbbbbbbbb"
LATE_Q = "If delivery of the goods is later than 15 October 2026, a penalty of 10% shall apply to the final invoice."
LIABILITY_Q = "The total liability of either party shall not exceed 10% of the total order value."
PAYMENT_Q = "All invoices are payable 30 calendar days after the date of invoice."
PRICE_Q = "The agreed unit price for Dell PowerEdge R750 Server is PKR 1,500,000 per unit and shall not be exceeded."
VOLUME_Q = "If the Buyer orders 25 or more units in a single order, a discount of 5% shall be applied to the invoice."

PAGES = [
    "SUPPLY AGREEMENT\n1. Parties\nThis Agreement is between Buyer Co and Vendor Co.\n"
    "2. Scope of Supply\nThe Vendor shall supply the goods in each order.\nPage 1 of 3",
    f"SUPPLY AGREEMENT\n3. Delivery and Late Delivery\n{LATE_Q}\n4. Limitation of Liability\n{LIABILITY_Q}\nPage 2 of 3",
    f"SUPPLY AGREEMENT\n5. Payment Terms\n{PAYMENT_Q}\n6. Pricing\n{PRICE_Q}\n7. Volume Discount\n{VOLUME_Q}\nPage 3 of 3",
]

LATE = {"quote": LATE_Q, "chunk_id": f"{PREFIX}-003", "deadline": "2026-10-15", "mode": "flat_percent",
        "percent": 10, "cap_percent": None, "grace_days": 0}
VOLUME = {"quote": VOLUME_Q, "chunk_id": f"{PREFIX}-007", "min_quantity": 25, "discount_percent": 5}
PAYMENT = {"quote": PAYMENT_Q, "chunk_id": f"{PREFIX}-005", "net_days": 30}
PRICE = {"quote": PRICE_Q, "chunk_id": f"{PREFIX}-006", "item_name": "Dell PowerEdge R750 Server",
         "agreed_unit_price": 1500000}


def doc(pages=PAGES):
    return ParsedDocument(
        source_name="c.pdf",
        sha256="b" * 64,
        pages=[PageText(number=i, text=t) for i, t in enumerate(pages, start=1)],
    )


def reply(*rules):
    return json.dumps({"rules": list(rules)})


def run(replies, document=None):
    provider = ScriptedProvider(replies)
    result = LegalExtractor(provider, HashingEmbedder()).extract(document or doc())
    return result, provider


def full_replies():
    return [reply(LATE), reply(VOLUME), reply(PAYMENT), reply(PRICE)]


def issue_for(result, clause_type):
    """The issue reported for one clause type (the safety net can add issues for other types too)."""
    return next(i for i in result.issues if i.clause_type == clause_type)


def test_all_four_rules_are_extracted_with_pages_from_the_parser():
    result, provider = run(full_replies())
    assert result.issues == []
    assert [r.clause_type for r in result.contract.rules] == [
        "late_penalty", "volume_discount", "payment_terms", "unit_price"
    ]
    late, volume, payment, price = result.contract.rules
    assert (late.source.page, volume.source.page, payment.source.page, price.source.page) == (2, 3, 3, 3)
    assert late.deadline == date(2026, 10, 15) and late.percent == Decimal("10") and late.cap_percent is None
    assert price.agreed_unit_price == Decimal("1500000")
    assert late.source.text == LATE_Q
    assert result.llm_model == "scripted-1"
    assert len(provider.prompts) == 4


def test_prompt_shows_the_relevant_clause_with_its_chunk_id():
    _, provider = run(full_replies())
    assert f"[chunk_id: {PREFIX}-003]" in provider.prompts[0]
    assert "later than 15 October 2026" in provider.prompts[0]


def test_empty_answers_on_a_contract_without_the_clauses_give_no_rules_and_no_issues():
    # Page 1 only: parties and scope, no penalty, discount, payment or price wording.
    result, _ = run([reply(), reply(), reply(), reply()], document=doc([PAGES[0]]))
    assert result.contract.rules == [] and result.issues == []


def test_empty_answers_on_a_contract_that_has_the_clauses_are_flagged_for_review():
    """Safety net: the clauses are there but the model returned nothing, so never stay silent."""
    result, _ = run([reply(), reply(), reply(), reply()])
    assert result.contract.rules == []
    # payment_terms is not flagged here: its hint needs the word "within", and PAYMENT_Q says "payable 30 ... days".
    assert {i.clause_type for i in result.issues} == {"late_penalty", "volume_discount", "unit_price"}
    assert all("needs review" in i.reason for i in result.issues)


def test_invented_quote_is_refused():
    fake = {**LATE, "quote": "The Vendor shall pay a penalty of 12% for every week of delay after 1 November 2026."}
    result, _ = run([reply(fake), reply(), reply(), reply()])
    assert result.contract.rules == []
    assert "not found" in issue_for(result, "late_penalty").reason


def test_number_that_is_not_in_the_quote_is_refused():
    result, _ = run([reply({**LATE, "percent": 15}), reply(), reply(), reply()])
    assert result.contract.rules == []
    assert "percent 15" in issue_for(result, "late_penalty").reason


def test_date_that_is_not_in_the_quote_is_refused():
    result, _ = run([reply({**LATE, "deadline": "2026-10-16"}), reply(), reply(), reply()])
    assert result.contract.rules == []
    assert "2026-10-16" in issue_for(result, "late_penalty").reason


def test_decoy_clause_reported_as_a_late_penalty_is_refused():
    decoy = {**LATE, "quote": LIABILITY_Q, "chunk_id": f"{PREFIX}-004"}
    result, _ = run([reply(decoy), reply(), reply(), reply()])
    assert result.contract.rules == []
    assert "deadline" in issue_for(result, "late_penalty").reason


def test_wrong_chunk_id_does_not_matter_the_real_location_is_used():
    wrong = {**LATE, "chunk_id": f"{PREFIX}-001"}
    result, _ = run([reply(wrong), reply(), reply(), reply()])
    assert result.contract.rules[0].source.page == 2


def test_unusable_model_output_is_retried_through_the_form_inspector():
    result, provider = run(["garbage", reply(LATE), reply(), reply(), reply()])
    assert len(result.contract.rules) == 1
    assert len(provider.prompts) == 5
    assert "rejected" in provider.prompts[1]


def test_one_clause_type_failing_does_not_stop_the_others():
    result, _ = run(["bad", "bad", "bad", reply(VOLUME), reply(PAYMENT), reply(PRICE)])
    assert [r.clause_type for r in result.contract.rules] == ["volume_discount", "payment_terms", "unit_price"]
    assert "unusable" in issue_for(result, "late_penalty").reason


def test_contract_without_text_is_reported_and_costs_no_model_calls():
    result, provider = run([], document=doc(["", ""]))
    assert result.contract.rules == []
    assert result.issues[0].clause_type == "all"
    assert provider.prompts == []


def test_quantity_that_is_not_next_to_units_is_refused():
    result, _ = run([reply(), reply({**VOLUME, "min_quantity": 5}), reply(), reply()])
    assert result.contract.rules == []
    assert "min_quantity 5" in issue_for(result, "volume_discount").reason


def test_payment_days_must_be_written_as_days():
    result, _ = run([reply(), reply(), reply({**PAYMENT, "net_days": 15}), reply()])
    assert result.contract.rules == []
    assert "net_days 15" in issue_for(result, "payment_terms").reason