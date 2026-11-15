"""A unit price rule may take its item name and rupee price from the whole clause of its quote."""

import json
from decimal import Decimal

from auditagent.agents.legal_extractor import LegalExtractor
from auditagent.ingestion.embedder import HashingEmbedder
from auditagent.llm.fake import ScriptedProvider
from auditagent.schemas.document import PageText, ParsedDocument

CLAUSE = (
    "8.1 The price payable for each unit of the Lenovo ThinkPad T14 Laptop is PKR 275,000 "
    '(the "Agreed Unit Price"). The Vendor shall not invoice above the Agreed Unit Price.'
)
QUOTE = 'is PKR 275,000 (the "Agreed Unit Price")'
NO_PRICE_QUOTE = "The Vendor shall not invoice above the Agreed Unit Price."
PAGES = [
    "SUPPLY AGREEMENT\n1. Parties\nThis Agreement is between Buyer Co and Vendor Co.\nPage 1 of 2",
    f"SUPPLY AGREEMENT\n8. Price\n{CLAUSE}\nPage 2 of 2",
]
EMPTY = json.dumps({"rules": []})


def extract(**changes):
    """Run Agent 1 with a model that answers one unit price rule (the other three types are empty)."""
    rule = {
        "quote": QUOTE,
        "chunk_id": "b-002",
        "item_name": "Lenovo ThinkPad T14 Laptop",
        "agreed_unit_price": 275000,
        **changes,
    }
    provider = ScriptedProvider([EMPTY, EMPTY, EMPTY, json.dumps({"rules": [rule]})])
    doc = ParsedDocument(
        source_name="c.pdf",
        sha256="b" * 64,
        pages=[PageText(number=i, text=t) for i, t in enumerate(PAGES, start=1)],
    )
    return LegalExtractor(provider, HashingEmbedder()).extract(doc)


def test_an_item_name_that_is_in_the_clause_but_not_in_the_quote_is_accepted():
    result = extract()
    assert result.issues == []
    rule = result.contract.rules[0]
    assert rule.item_name == "Lenovo ThinkPad T14 Laptop"
    assert rule.agreed_unit_price == Decimal(275000)


def test_an_item_that_the_clause_does_not_name_is_refused():
    result = extract(item_name="Dell PowerEdge R750 Server")
    assert result.contract.rules == []
    assert any(i.clause_type == "unit_price" for i in result.issues)


def test_a_price_that_the_clause_does_not_write_as_rupees_is_refused():
    result = extract(quote=NO_PRICE_QUOTE, agreed_unit_price=1)
    assert result.contract.rules == []
    assert any(i.clause_type == "unit_price" for i in result.issues)


def test_a_price_from_the_clause_is_accepted_when_the_quote_lacks_it():
    result = extract(quote=NO_PRICE_QUOTE)
    assert result.issues == []
    assert result.contract.rules[0].agreed_unit_price == Decimal(275000)
