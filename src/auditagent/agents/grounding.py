"""Checks that make every extracted rule prove itself against the real contract text."""

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from auditagent.ingestion.pdf_parser import normalize_for_match
from auditagent.schemas.chunk import Chunk

MIN_QUOTE_CHARS = 25
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
_WORD_IN_BRACKETS = r"(?:\([A-Za-z][A-Za-z\- ]*\)\s*)?"  # e.g. "40 (forty) units"
PERCENT_RE = re.compile(rf"(\d+(?:\.\d+)?)\)?\s*{_WORD_IN_BRACKETS}(?:%|per\s?cent\b)", re.IGNORECASE)
DAYS_RE = re.compile(
    rf"\(?(\d+)\)?\s*{_WORD_IN_BRACKETS}(?:(?:calendar|business|working|consecutive)\s+)?days?\b"
    r"|\bnet\s*(\d+)\b",
    re.IGNORECASE,
)
UNITS_RE = re.compile(
    rf"(\d[\d,]*)\)?\s*{_WORD_IN_BRACKETS}(?:or\s+(?:more|above|over|greater)\s+)?"
    r"(?:units?|pieces?|items?|devices?|licen[cs]es?|seats?)\b",
    re.IGNORECASE,
)
# A defined term that names a date: (the "Delivery Deadline") or "Delivery Date" means ...
# Only terms ending in Deadline, Date or Day count, so party names such as (the "Vendor") never link two clauses.
_DEFINED_DATE_TERM_RE = re.compile(
    r'"((?:[A-Z][A-Za-z]* ){0,3}(?:Deadline|Date|Day))"(?=\s*\)|\s+(?:shall\s+)?means\b)'
)
_MONTHS = (
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
)
_QUOTES = {0x201C: '"', 0x201D: '"', 0x2018: "'", 0x2019: "'"}


def _fold(text: str) -> str:
    """Flatten whitespace and straighten curly quotes so harmless differences do not matter."""
    return normalize_for_match(text).translate(_QUOTES)


def numbers_in(text: str) -> set[Decimal]:
    """Every number written in the text (thousands commas removed)."""
    found = set()
    for token in _NUMBER.findall(text):
        try:
            found.add(Decimal(token.replace(",", "")))
        except InvalidOperation:
            continue
    return found


def number_in(value, text: str) -> bool:
    """True if `value` is written somewhere in `text` as a number."""
    return Decimal(str(value)) in numbers_in(text)


def _values(pattern: re.Pattern, text: str) -> set[Decimal]:
    found = set()
    for match in pattern.finditer(text):
        for group in match.groups():
            if group:
                found.add(Decimal(group.replace(",", "")))
    return found


def percent_in(value, text: str) -> bool:
    """True if `value` is written as a percentage (10%, 10 percent) in `text`."""
    return Decimal(str(value)) in _values(PERCENT_RE, text)


def days_in(value, text: str) -> bool:
    """True if `value` is written as a number of days (30 days, Net 30, (30) calendar days)."""
    return Decimal(str(value)) in _values(DAYS_RE, text)


def units_in(value, text: str) -> bool:
    """True if `value` is written as a number of units (25 or more units)."""
    return Decimal(str(value)) in _values(UNITS_RE, text)


def date_in(day: date, text: str) -> bool:
    """True if `day` is written in `text` in any common format."""
    t = _fold(text).lower()
    month = _MONTHS[day.month - 1]
    forms = {
        day.isoformat(),
        f"{day.day:02d}/{day.month:02d}/{day.year}",
        f"{day.day}/{day.month}/{day.year}",
        f"{day.day:02d}-{day.month:02d}-{day.year}",
    }
    for d in {str(day.day), f"{day.day:02d}"}:
        for m in {month, month[:3]}:
            forms |= {f"{d} {m} {day.year}", f"{d}-{m}-{day.year}", f"{m} {d}, {day.year}", f"{m} {d} {day.year}"}
            for suffix in ("st", "nd", "rd", "th"):
                forms |= {f"{d}{suffix} {m} {day.year}", f"{d}{suffix} of {m} {day.year}", f"{m} {d}{suffix}, {day.year}"}
    return any(form in t for form in forms)


def defined_terms(text: str) -> set[str]:
    """The date terms the text defines, e.g. (the "Delivery Deadline") or "Delivery Date" means ..."""
    return set(_DEFINED_DATE_TERM_RE.findall(_fold(text)))


def shares_defined_term(definition: str, usage: str) -> bool:
    """True if `usage` uses a date term that `definition` defines (case matters: defined terms are capitalised)."""
    folded = _fold(usage)
    return any(term in folded for term in defined_terms(definition))


def locate_quote(chunks: list[Chunk], quote: str, cited_id: str | None = None) -> Chunk | None:
    """The chunk that really contains the quote, or None if the quote is not in the contract."""
    needle = _fold(quote)
    if len(needle) < MIN_QUOTE_CHARS:
        return None
    holders = [c for c in chunks if needle in _fold(c.text)]
    if not holders:
        return None
    for chunk in holders:
        if chunk.chunk_id == cited_id:
            return chunk
    return holders[0]