from datetime import date
from decimal import Decimal

import pytest

from auditagent.agents.grounding import (
    date_in,
    days_in,
    defined_terms,
    locate_quote,
    number_in,
    numbers_in,
    percent_in,
    shares_defined_term,
    units_in,
)
from auditagent.schemas.chunk import Chunk

QUOTE = "If delivery of the goods is later than 15 October 2026, a penalty of 10% shall apply to the final invoice."


def chunk(chunk_id, text, page=1):
    return Chunk(chunk_id=chunk_id, page_start=page, page_end=page, heading="", text=text)


def test_numbers_in_reads_commas_and_decimals():
    found = numbers_in("PKR 1,500,000 and 2.5% by 15 October 2026.")
    assert found == {Decimal(1500000), Decimal("2.5"), Decimal(15), Decimal(2026)}


def test_number_in_matches_whole_numbers_only():
    text = "a penalty of 10% shall apply"
    assert number_in(10, text) and number_in(10.0, text) and number_in(Decimal("10"), text)
    assert not number_in(1, text)  # "1" is only a piece of "10"
    assert not number_in(15, text)


@pytest.mark.parametrize(
    "text",
    [
        "later than 15 October 2026",
        "later than 15th October 2026",
        "later than October 15, 2026",
        "later than 15-Oct-2026",
        "later than 15/10/2026",
        "later than 2026-10-15",
        "later than 15 october 2026",
    ],
)
def test_date_in_accepts_common_formats(text):
    assert date_in(date(2026, 10, 15), text)


@pytest.mark.parametrize(
    "text", ["later than 16 October 2026", "later than 15 November 2026", "later than 15 October 2025"]
)
def test_date_in_rejects_other_dates(text):
    assert not date_in(date(2026, 10, 15), text)


def test_quote_is_found_despite_spacing_and_curly_quotes():
    chunks = [chunk("a-1", "3. Delivery " + QUOTE.replace("goods", "\u201cgoods\u201d"))]
    messy = QUOTE.replace(" ", "  ").replace("goods", '"goods"')
    assert locate_quote(chunks, messy).chunk_id == "a-1"


def test_quote_that_is_not_in_the_contract_is_refused():
    chunks = [chunk("a-1", "3. Delivery " + QUOTE)]
    assert locate_quote(chunks, "A penalty of 12% applies for every week of delay after 1 November.") is None


def test_very_short_quotes_are_refused():
    chunks = [chunk("a-1", "3. Delivery " + QUOTE)]
    assert locate_quote(chunks, "10%") is None


def test_cited_chunk_wins_when_the_quote_appears_twice():
    chunks = [chunk("a-1", QUOTE, page=1), chunk("a-2", QUOTE, page=2)]
    assert locate_quote(chunks, QUOTE, cited_id="a-2").chunk_id == "a-2"
    assert locate_quote(chunks, QUOTE, cited_id="zzz").chunk_id == "a-1"


def test_percent_must_be_written_as_a_percentage_not_as_a_date():
    """The day '15' in '15 October' must not count as '15%'."""
    assert percent_in(10, QUOTE) and not percent_in(15, QUOTE)
    assert percent_in(2.5, "a charge of 2.5 percent applies") and percent_in(7, "7 per cent")


def test_days_are_read_in_common_legal_styles():
    assert days_in(30, "payable within thirty (30) days of the invoice")
    assert days_in(30, "payable 30 calendar days after the date")
    assert days_in(45, "settle invoices on Net 45 terms")
    assert days_in(3, "No penalty applies if the delay is not more than 3 days.")
    assert not days_in(15, QUOTE)  # 15 October is a date, not a number of days


def test_units_are_read_next_to_the_word_units():
    assert units_in(25, "orders 25 or more units in a single order")
    assert units_in(50, "any order of 50 units or above")
    assert units_in(25, "at least 25 units")
    assert not units_in(5, "a discount of 5% on orders of 25 units")


@pytest.mark.parametrize(
    "text",
    [
        "40 units",
        "forty (40) units",
        "40 (forty) units",
        "forty (40) or more Units",
        "at least forty (40) units of Equipment",
        "orders of 40 or more units",
    ],
)
def test_units_are_read_in_every_common_legal_style(text):
    assert units_in(40, text)


def test_words_in_brackets_do_not_hide_days_or_percentages():
    assert days_in(30, "within thirty (30) days") and days_in(30, "within 30 (thirty) calendar days")
    assert percent_in(8, "eight percent (8%)") and percent_in(8, "8 (eight) per cent")
    assert not units_in(30, "within thirty (30) days")


def test_defined_date_terms_are_found_in_common_styles():
    assert defined_terms('on or before 31 October 2026 (the "Delivery Deadline"), at its own cost') == {"Delivery Deadline"}
    assert defined_terms('"Delivery Date" means 31 October 2026') == {"Delivery Date"}
    assert defined_terms("(the \u201cDelivery Deadline\u201d)") == {"Delivery Deadline"}


def test_party_names_and_other_terms_are_not_date_terms():
    assert defined_terms('Vendor Co (the "Vendor") agrees') == set()
    assert defined_terms('the price is PKR 275,000 (the "Agreed Unit Price")') == set()


def test_a_penalty_clause_is_linked_to_the_clause_that_defines_its_date():
    definition = 'The Vendor shall deliver on or before 31 October 2026 (the "Delivery Deadline").'
    assert shares_defined_term(definition, "A penalty of 10% applies after the Delivery Deadline.")
    assert not shares_defined_term(definition, "A penalty of 10% applies after the date of delivery.")
    assert not shares_defined_term(definition, "A penalty applies after the delivery deadline.")  # case matters