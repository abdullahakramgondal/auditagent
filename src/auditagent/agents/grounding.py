"""Checks that make every extracted rule prove itself against the real contract text."""

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from auditagent.ingestion.pdf_parser import normalize_for_match
from auditagent.schemas.chunk import Chunk

MIN_QUOTE_CHARS = 25
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
_PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*(?:%|per\s?cent\b)", re.I)
_DAYS = re.compile(
    r"\(?(\d+)\)?\s*(?:(?:calendar|business|working|consecutive)\s+)?days?\b|\bnet\s*(\d+)\b", re.I
)
_UNITS = re.compile(
    r"(\d[\d,]*)\s*(?:\(\d+\)\s*)?(?:or\s+(?:more|above|over)\s+)?"
    r"(?:units?|pieces?|items?|devices?|licen[cs]es?|seats?)\b",
    re.I,
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
    return Decimal(str(value)) in _values(_PERCENT, text)


def days_in(value, text: str) -> bool:
    """True if `value` is written as a number of days (30 days, Net 30, (30) calendar days)."""
    return Decimal(str(value)) in _values(_DAYS, text)


def units_in(value, text: str) -> bool:
    """True if `value` is written as a number of units (25 or more units)."""
    return Decimal(str(value)) in _values(_UNITS, text)


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