"""The deadline date may sit in a neighbouring sentence of the SAME clause as the penalty.

A date in ANOTHER clause still needs a defined date term that the penalty quote uses.
"""

import json
from datetime import date

from auditagent.agents.legal_extractor import LegalExtractor
from auditagent.ingestion.embedder import HashingEmbedder
from auditagent.llm.fake import ScriptedProvider
from auditagent.schemas.document import PageText, ParsedDocument

DATE_S = (
    "For purposes of the agreed delivery arrangement, the delivery date relevant to the delay "
    "mechanism in this clause is 15 January 2027."
)
GRACE_S = "The first seven (7) days of delay after that date shall be free of a delivery penalty."
PENALTY_S = (
    "For each subsequent day of delay, the Vendor shall be liable to the Buyer for a penalty "
    "calculated at 0.5% of the invoice value, subject to an aggregate maximum of 5% of that "
    "invoice value."
)
SAME_CLAUSE = [
    "SUPPLY AGREEMENT\n1. Parties\nThis Agreement is between Buyer Co and Vendor Co.\nPage 1 of 2",
    f"SUPPLY AGREEMENT\n7. Delivery and Schedule\n7.3 {DATE_S} {GRACE_S} {PENALTY_S}\nPage 2 of 2",
]

# Two clauses: the date is in one, the penalty in the other, and no defined term links them.
DATE_Q = (
    "The Vendor shall deliver the goods on or before 31 October 2026, at its own cost and risk."
)
LATE_Q = "If the Vendor delivers the goods late, a penalty of 10% of the invoice value shall apply."
OTHER_CLAUSES = [
    f"SUPPLY AGREEMENT\n1. Parties\nThis Agreement is between Buyer Co and Vendor Co.\n2. Delivery\n{DATE_Q}\nPage 1 of 2",
    f"SUPPLY AGREEMENT\n3. Late Delivery\n{LATE_Q}\nPage 2 of 2",
]


def tail_rule(**changes):
    """The model's answer for the clause above: grace and penalty quoted, the date sentence apart."""
    base = {
        "quote": f"{GRACE_S} {PENALTY_S}",
        "chunk_id": "b-002",
        "deadline_quote": DATE_S,
        "deadline": "2027-01-15",
        "mode": "per_day_percent",
        "percent": 0.5,
        "cap_percent": 5.0,
        "grace_days": 7,
    }
    return {**base, **changes}


def extract(late_rule, pages):
    """Run Agent 1 on a contract with a model that answers `late_rule` for the late penalty."""
    empty = json.dumps({"rules": []})
    provider = ScriptedProvider([json.dumps({"rules": [late_rule]}), empty, empty, empty])
    doc = ParsedDocument(
        source_name="c.pdf",
        sha256="b" * 64,
        pages=[PageText(number=i, text=t) for i, t in enumerate(pages, start=1)],
    )
    return LegalExtractor(provider, HashingEmbedder()).extract(doc)


def issue_for(result, clause_type):
    """The issue reported for one clause type."""
    return next(i for i in result.issues if i.clause_type == clause_type)


def test_a_date_in_a_neighbouring_sentence_of_the_same_clause_is_accepted():
    """Regression (tb_06, tb_12): the model quoted the grace and penalty sentences and put the date apart."""
    result = extract(tail_rule(), SAME_CLAUSE)
    assert result.issues == []
    late = result.contract.rules[0]
    assert late.deadline == date(2027, 1, 15) and late.grace_days == 7
    assert late.source.text == f"{GRACE_S} {PENALTY_S}"
    assert late.deadline_source.page == 2 and late.deadline_source.text == DATE_S


def test_a_wrong_date_is_still_refused_when_the_clause_has_another_date():
    result = extract(tail_rule(deadline="2027-02-15"), SAME_CLAUSE)
    assert result.contract.rules == []
    assert "2027-02-15" in issue_for(result, "late_penalty").reason


def test_the_penalty_sentence_alone_is_refused_for_the_grace_days_not_for_the_date():
    result = extract(tail_rule(quote=PENALTY_S), SAME_CLAUSE)
    reason = issue_for(result, "late_penalty").reason
    assert result.contract.rules == []
    assert "grace_days 7" in reason and "deadline" not in reason


def test_a_date_in_another_clause_without_a_defined_term_is_still_refused():
    late_rule = {
        "quote": LATE_Q,
        "chunk_id": "b-003",
        "deadline_quote": DATE_Q,
        "deadline": "2026-10-31",
        "mode": "flat_percent",
        "percent": 10,
        "cap_percent": None,
        "grace_days": 0,
    }
    result = extract(late_rule, OTHER_CLAUSES)
    assert result.contract.rules == []
    assert "date term" in issue_for(result, "late_penalty").reason
