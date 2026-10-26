"""A quote must be one continuous passage of the contract: pieces joined with "..." are refused."""

import json

from auditagent.agents.legal_extractor import LegalExtractor
from auditagent.ingestion.embedder import HashingEmbedder
from auditagent.llm.fake import ScriptedProvider
from auditagent.schemas.document import PageText, ParsedDocument

DATE_Q = (
    "The Vendor shall deliver the goods on or before 31 October 2026 "
    '(the "Delivery Deadline"), at its own cost and risk.'
)
TERM_Q = (
    "If the Vendor delivers the goods after the Delivery Deadline, "
    "a penalty of 10% of the invoice value shall apply."
)
PAGES = [
    f"SUPPLY AGREEMENT\n1. Parties\nThis Agreement is between Buyer Co and Vendor Co.\n2. Delivery\n{DATE_Q}\nPage 1 of 2",
    f"SUPPLY AGREEMENT\n3. Late Delivery\n{TERM_Q}\nPage 2 of 2",
]
RULE = {
    "quote": TERM_Q,
    "chunk_id": "b-003",
    "deadline_quote": DATE_Q,
    "deadline": "2026-10-31",
    "mode": "flat_percent",
    "percent": 10,
    "cap_percent": None,
    "grace_days": 0,
}


def extract(rule):
    """Run Agent 1 on the two-clause contract with a model that answers `rule` for the late penalty."""
    empty = json.dumps({"rules": []})
    provider = ScriptedProvider([json.dumps({"rules": [rule]}), empty, empty, empty])
    doc = ParsedDocument(
        source_name="c.pdf",
        sha256="b" * 64,
        pages=[PageText(number=i, text=t) for i, t in enumerate(PAGES, start=1)],
    )
    return LegalExtractor(provider, HashingEmbedder()).extract(doc)


def test_a_quote_stitched_from_two_clauses_with_dots_is_refused():
    """Regression (tb_09): the model joined the date clause and the penalty clause with '...'."""
    result = extract({**RULE, "quote": f"{DATE_Q} ... {TERM_Q}"})
    assert result.contract.rules == []
    issue = next(i for i in result.issues if i.clause_type == "late_penalty")
    assert "not found" in issue.reason


def test_the_same_two_clauses_are_accepted_when_the_date_sentence_goes_in_deadline_quote():
    result = extract(RULE)
    assert result.issues == []
    late = result.contract.rules[0]
    assert late.source.text == TERM_Q
    assert late.deadline_source.text == DATE_Q
