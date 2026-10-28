"""A penalty clause may point at the clause that holds the delivery date ("clause 2.2")."""

import json
from datetime import date

from auditagent.agents.grounding import clause_refs, is_clause
from auditagent.agents.legal_extractor import LegalExtractor
from auditagent.ingestion.embedder import HashingEmbedder
from auditagent.llm.fake import ScriptedProvider
from auditagent.schemas.chunk import Chunk
from auditagent.schemas.document import PageText, ParsedDocument

DATE_Q = "The Equipment shall be delivered no later than 10 June 2027."
OTHER_Q = "Payment shall be made by bank transfer to the account named in the invoice."
LATE_Q = (
    "If delivery takes place after the date stated in clause 2.2, "
    "a penalty of 10% of the invoice value shall apply."
)
WRONG_Q = (
    "If delivery takes place after the date stated in clause 2.3, "
    "a penalty of 10% of the invoice value shall apply."
)


def chunk(heading):
    """A chunk whose heading is the given text."""
    return Chunk(chunk_id="x-001", page_start=1, page_end=1, heading=heading, text=heading)


def pages_for(penalty_quote):
    """Clause 2.2 holds the date, clause 2.3 is about payment, clause 3.1 is the penalty."""
    first = (
        "SUPPLY AGREEMENT\n1. Parties\nThis Agreement is between Buyer Co and Vendor Co.\n"
        f"2. Delivery\n2.2 {DATE_Q}\n2.3 {OTHER_Q}\nPage 1 of 2"
    )
    second = f"SUPPLY AGREEMENT\n3. Late Delivery\n3.1 {penalty_quote}\nPage 2 of 2"
    return [first, second]


def late_rule(penalty_quote):
    """The model's answer: the penalty sentence, and the date sentence of clause 2.2 apart."""
    return {
        "quote": penalty_quote,
        "chunk_id": "b-003",
        "deadline_quote": DATE_Q,
        "deadline": "2027-06-10",
        "mode": "flat_percent",
        "percent": 10,
        "cap_percent": None,
        "grace_days": 0,
    }


def extract(penalty_quote):
    """Run Agent 1 on the two-page contract with a model that answers late_rule for the late penalty."""
    empty = json.dumps({"rules": []})
    provider = ScriptedProvider(
        [json.dumps({"rules": [late_rule(penalty_quote)]}), empty, empty, empty]
    )
    doc = ParsedDocument(
        source_name="c.pdf",
        sha256="b" * 64,
        pages=[PageText(number=i, text=t) for i, t in enumerate(pages_for(penalty_quote), start=1)],
    )
    return LegalExtractor(provider, HashingEmbedder()).extract(doc)


def test_clause_references_are_read_with_their_numbers():
    assert clause_refs("the date stated in clause 5.2.") == {"5.2"}
    assert clause_refs("see Clause 7.1 and Section 3 below") == {"7.1", "3"}
    assert clause_refs("no reference here") == set()


def test_a_clause_is_recognised_by_the_number_at_the_start_of_its_heading():
    assert is_clause(chunk("5.2 Scheduled delivery date. The Equipment"), "5.2")
    assert is_clause(chunk("5.2. Delivery"), "5.2")
    assert not is_clause(chunk("5.2.1 Sub-clause"), "5.2")
    assert not is_clause(chunk("5.20 Other"), "5.2")
    assert not is_clause(chunk("15.2 Other"), "5.2")


def test_a_date_in_the_clause_that_the_penalty_cites_is_accepted():
    """Regression (tb_14, tb_16): 'the date stated in clause 5.2' pointed at the date clause."""
    result = extract(LATE_Q)
    assert result.issues == []
    late = result.contract.rules[0]
    assert late.deadline == date(2027, 6, 10)
    assert late.source.page == 2 and late.source.text == LATE_Q
    assert late.deadline_source.page == 1 and late.deadline_source.text == DATE_Q


def test_a_date_is_refused_when_the_cited_clause_is_not_the_one_that_holds_it():
    result = extract(WRONG_Q)
    assert result.contract.rules == []
    issue = next(i for i in result.issues if i.clause_type == "late_penalty")
    assert "refers to the clause" in issue.reason
