"""Only a per-day penalty has a cap. A per-day cap equal to the percentage needs two mentions."""

import json
from decimal import Decimal

from auditagent.agents.grounding import percent_count
from auditagent.agents.legal_extractor import LegalExtractor
from auditagent.ingestion.embedder import HashingEmbedder
from auditagent.llm.fake import ScriptedProvider
from auditagent.schemas.document import PageText, ParsedDocument

FLAT_Q = (
    "If the Vendor delivers the goods after 15 October 2026, a penalty of 10% of the invoice "
    "value shall apply once only."
)
PER_DAY_Q = (
    "If the Vendor delivers the goods after 15 October 2026, a penalty of 8% of the invoice value "
    "shall apply for each day of delay, up to a maximum of 8% of that invoice value."
)
PER_DAY_ONCE_Q = (
    "If the Vendor delivers the goods after 15 October 2026, a penalty of 8% of the invoice value "
    "shall apply for each day of delay."
)


def rule(quote, **changes):
    """The model's answer for a late penalty whose date is written in the quote."""
    base = {
        "quote": quote,
        "chunk_id": "b-002",
        "deadline_quote": quote,
        "deadline": "2026-10-15",
        "mode": "flat_percent",
        "percent": 10,
        "cap_percent": None,
        "grace_days": 0,
    }
    return {**base, **changes}


def extract(late_rule, quote):
    """Run Agent 1 on a two-page contract whose second page holds `quote`."""
    pages = [
        "SUPPLY AGREEMENT\n1. Parties\nThis Agreement is between Buyer Co and Vendor Co.\nPage 1 of 2",
        f"SUPPLY AGREEMENT\n3. Late Delivery\n{quote}\nPage 2 of 2",
    ]
    empty = json.dumps({"rules": []})
    provider = ScriptedProvider([json.dumps({"rules": [late_rule]}), empty, empty, empty])
    doc = ParsedDocument(
        source_name="c.pdf",
        sha256="b" * 64,
        pages=[PageText(number=i, text=t) for i, t in enumerate(pages, start=1)],
    )
    return LegalExtractor(provider, HashingEmbedder()).extract(doc)


def test_percent_count_counts_every_mention_of_the_value():
    assert percent_count(10, "a penalty of 10% and a maximum of 10%") == 2
    assert percent_count(10, "ten percent (10%)") == 1
    assert percent_count(5, "a penalty of 10%") == 0
    assert percent_count(2.5, "2.5 percent now and 2.5% later") == 2


def test_a_flat_penalty_ignores_a_cap_equal_to_the_percentage():
    """Regression (tb_01, tb_04): the model reported cap_percent 10 for a flat 10% penalty."""
    result = extract(rule(FLAT_Q, cap_percent=10.0), FLAT_Q)
    assert result.issues == []
    assert result.contract.rules[0].cap_percent is None


def test_a_flat_penalty_ignores_any_other_cap_too():
    result = extract(rule(FLAT_Q, cap_percent=12.0), FLAT_Q)
    assert result.issues == []
    assert result.contract.rules[0].cap_percent is None


def test_a_flat_penalty_without_a_cap_is_accepted():
    result = extract(rule(FLAT_Q), FLAT_Q)
    assert result.issues == []
    assert result.contract.rules[0].cap_percent is None


def test_a_per_day_cap_equal_to_the_percentage_written_once_is_refused():
    late_rule = rule(PER_DAY_ONCE_Q, mode="per_day_percent", percent=8, cap_percent=8.0)
    result = extract(late_rule, PER_DAY_ONCE_Q)
    assert result.contract.rules == []
    issue = next(i for i in result.issues if i.clause_type == "late_penalty")
    assert "same number as percent" in issue.reason


def test_a_per_day_cap_equal_to_the_percentage_is_accepted_when_the_quote_writes_it_twice():
    late_rule = rule(PER_DAY_Q, mode="per_day_percent", percent=8, cap_percent=8.0)
    result = extract(late_rule, PER_DAY_Q)
    assert result.issues == []
    late = result.contract.rules[0]
    assert late.percent == Decimal(8) and late.cap_percent == Decimal(8)
