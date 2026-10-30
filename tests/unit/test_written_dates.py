"""A deadline written as 15 October 2026 is read as a date, and is still proven against the quote.

TODO item 60: the local qwen2.5:7b model answered '15 October 2026' where the form asks YYYY-MM-DD.
"""

import json
from datetime import date

import pytest

from auditagent.agents.grounding import parse_written_date
from auditagent.agents.legal_extractor import LegalExtractor
from auditagent.ingestion.embedder import HashingEmbedder
from auditagent.llm.fake import ScriptedProvider
from auditagent.schemas.document import PageText, ParsedDocument

QUOTE = (
    "If delivery of the goods is later than 15 October 2026, "
    "a penalty of 10% shall apply to the final invoice."
)
PAGES = [
    "SUPPLY AGREEMENT\n1. Parties\nThis Agreement is between Buyer Co and Vendor Co.\nPage 1 of 2",
    f"SUPPLY AGREEMENT\n3. Late Delivery\n{QUOTE}\nPage 2 of 2",
]


@pytest.mark.parametrize(
    "text",
    [
        "2026-10-15",
        "15 October 2026",
        "15th October 2026",
        "15th of October, 2026",
        "October 15, 2026",
        "October 15th 2026",
        "15-Oct-2026",
        "15 Oct. 2026",
        "  15   october   2026 ",
    ],
)
def test_clear_written_dates_are_read(text):
    assert parse_written_date(text) == date(2026, 10, 15)


def test_september_may_be_written_sept():
    assert parse_written_date("5 Sept 2026") == date(2026, 9, 5)


@pytest.mark.parametrize(
    "text",
    [
        "15/10/2026",  # the day or the month first? never guessed
        "2026-13-01",
        "31 February 2026",
        "15 Octobre 2026",
        "October 2026",
        "next Tuesday",
        "",
    ],
)
def test_dates_that_cannot_be_read_without_guessing_give_none(text):
    assert parse_written_date(text) is None


def late_rule(deadline):
    return {
        "quote": QUOTE,
        "chunk_id": "b-002",
        "deadline_quote": QUOTE,
        "deadline": deadline,
        "mode": "flat_percent",
        "percent": 10,
        "cap_percent": None,
        "grace_days": 0,
    }


def extract(deadline):
    empty = json.dumps({"rules": []})
    replies = [json.dumps({"rules": [late_rule(deadline)]}), empty, empty, empty]
    doc = ParsedDocument(
        source_name="c.pdf",
        sha256="b" * 64,
        pages=[PageText(number=i, text=t) for i, t in enumerate(PAGES, start=1)],
    )
    return LegalExtractor(ScriptedProvider(replies), HashingEmbedder()).extract(doc)


def test_a_written_deadline_that_is_in_the_quote_is_accepted():
    result = extract("15 October 2026")
    assert result.issues == []
    assert result.contract.rules[0].deadline == date(2026, 10, 15)


def test_a_written_deadline_that_is_not_in_the_quote_is_still_refused():
    result = extract("16 October 2026")
    assert result.contract.rules == []
    issue = next(i for i in result.issues if i.clause_type == "late_penalty")
    assert "not written in the quote" in issue.reason


def test_an_ambiguous_numeric_deadline_is_refused_even_when_it_is_in_the_text():
    result = extract("15/10/2026")
    assert result.contract.rules == []
    issue = next(i for i in result.issues if i.clause_type == "late_penalty")
    assert "can be read" in issue.reason
