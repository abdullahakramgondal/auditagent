"""Review a Tier B contract PDF against its spec: are the required values there, and is anything extra?

Run:  python -m data.tier_b.check_contract tb_01
It reads data/tier_b/pdf/<id>.pdf (exactly what the extractor will see) and data/tier_b/specs/<id>.json.
A human still decides: this only points at the places worth reading.
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

from auditagent.agents.grounding import (
    DAYS_RE,
    PERCENT_RE,
    UNITS_RE,
    date_in,
    days_in,
    number_in,
    percent_in,
    units_in,
)
from auditagent.ingestion.chunker import chunk_document
from auditagent.ingestion.pdf_parser import normalize_for_match, parse_pdf

TIER_DIR = Path(__file__).resolve().parent
DECOY_PERCENTS = {2, 10}  # late payment charge, liability cap (see make_prompts.DECOYS)
DECOY_DAYS = {30}  # termination notice

_PKR = re.compile(r"(?<![A-Za-z])(?:PKR|Rs\.?)\s*(\d[\d,]*(?:\.\d+)?)", re.IGNORECASE)
_WORDS = (
    "one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|"
    "seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|half"
)
_NUMBER_WORDS = re.compile(
    rf"\b(?:{_WORDS})(?:[-\s](?:{_WORDS}))?\s+(?:per\s?cent|percent|(?:calendar\s+|business\s+|working\s+)?days?)\b(?!\s*\(\s*\d)",
    re.IGNORECASE,
)


def _to_number(token: str) -> float | None:
    try:
        return float(token.replace(",", ""))
    except ValueError:
        return None


def _context(text: str, start: int, end: int, width: int = 70) -> str:
    return normalize_for_match(text[max(0, start - width) : end + width])


def _expected(spec: dict) -> dict:
    sets = {"percent": set(), "days": set(), "units": set(), "amounts": set()}
    for r in spec["rules"]:
        kind = r["clause_type"]
        if kind == "late_penalty":
            sets["percent"].add(float(r["percent"]))
            if r.get("cap_percent"):
                sets["percent"].add(float(r["cap_percent"]))
            if r.get("grace_days"):
                sets["days"].add(float(r["grace_days"]))
        elif kind == "volume_discount":
            sets["units"].add(float(r["min_quantity"]))
            sets["percent"].add(float(r["discount_percent"]))
        elif kind == "payment_terms":
            sets["days"].add(float(r["net_days"]))
        else:
            sets["amounts"].add(float(r["agreed_unit_price"]))
    return sets


def _checks(spec: dict) -> list[tuple[str, callable]]:
    checks = []
    for r in spec["rules"]:
        kind = r["clause_type"]
        if kind == "late_penalty":
            day = date.fromisoformat(r["deadline"])
            checks.append(
                (f"late_penalty deadline {r['deadline']}", lambda t, d=day: date_in(d, t))
            )
            checks.append(
                (f"late_penalty percent {r['percent']}", lambda t, v=r["percent"]: percent_in(v, t))
            )
            if r.get("cap_percent"):
                checks.append(
                    (
                        f"late_penalty cap {r['cap_percent']}",
                        lambda t, v=r["cap_percent"]: percent_in(v, t),
                    )
                )
            if r.get("grace_days"):
                checks.append(
                    (
                        f"late_penalty grace {r['grace_days']} days",
                        lambda t, v=r["grace_days"]: days_in(v, t),
                    )
                )
        elif kind == "volume_discount":
            checks.append(
                (
                    f"volume_discount {r['min_quantity']} units",
                    lambda t, v=r["min_quantity"]: units_in(v, t),
                )
            )
            checks.append(
                (
                    f"volume_discount {r['discount_percent']}%",
                    lambda t, v=r["discount_percent"]: percent_in(v, t),
                )
            )
        elif kind == "payment_terms":
            checks.append(
                (f"payment_terms {r['net_days']} days", lambda t, v=r["net_days"]: days_in(v, t))
            )
        else:
            name = normalize_for_match(r["item_name"]).lower()
            checks.append(
                (
                    f"unit_price item {r['item_name']}",
                    lambda t, n=name: n in normalize_for_match(t).lower(),
                )
            )
            checks.append(
                (
                    f"unit_price PKR {r['agreed_unit_price']}",
                    lambda t, v=r["agreed_unit_price"]: number_in(v, t),
                )
            )
    return checks


def review_text(spec: dict, pages: list[str]) -> dict:
    """Pure function: required values found (with page), unexpected numbers, and number words."""
    required = []
    for label, check in _checks(spec):
        page = next((i for i, text in enumerate(pages, start=1) if check(text)), None)
        required.append((label, page))

    expected = _expected(spec)
    allowed = {
        "percent": expected["percent"] | DECOY_PERCENTS,
        "days": expected["days"] | DECOY_DAYS,
        "units": expected["units"],
        "amounts": expected["amounts"],
    }
    patterns = {"percent": PERCENT_RE, "days": DAYS_RE, "units": UNITS_RE, "amounts": _PKR}
    unexpected, number_words = [], []
    for page_no, text in enumerate(pages, start=1):
        for kind, pattern in patterns.items():
            for m in pattern.finditer(text):
                token = next((g for g in m.groups() if g), None)
                value = _to_number(token) if token else None
                if value is not None and value not in allowed[kind]:
                    unexpected.append((page_no, kind, token, _context(text, m.start(), m.end())))
        for m in _NUMBER_WORDS.finditer(text):
            number_words.append((page_no, m.group(0), _context(text, m.start(), m.end())))
    return {"required": required, "unexpected": unexpected, "number_words": number_words}


def main(case_id: str) -> None:
    spec = json.loads((TIER_DIR / "specs" / f"{case_id}.json").read_text())
    doc = parse_pdf(TIER_DIR / "pdf" / f"{case_id}.pdf")
    pages = [p.text for p in doc.pages]
    chunks = chunk_document(doc)
    headings = [c.heading for c in chunks if c.heading]
    words = sum(len(t.split()) for t in pages)
    report = review_text(spec, pages)

    print(f"== {case_id}  writer: {spec.get('writer')}  pages: {doc.page_count}  words: {words}")
    print(f"chunks: {len(chunks)}  with numbered headings: {len(headings)}")
    print(
        "first headings:",
        headings[:6] or "NONE FOUND (the chunker will treat this text as one block)",
    )
    if doc.warnings:
        print("parser warnings:", doc.warnings)

    print("\nREQUIRED VALUES (page where found)")
    for label, page in report["required"]:
        print(f"  {'OK     ' if page else 'MISSING'} {label}" + (f"   page {page}" if page else ""))

    print(
        f"\nUNEXPECTED NUMBERS ({len(report['unexpected'])}): read each one, is it a real extra rule?"
    )
    for page, kind, value, ctx in report["unexpected"]:
        print(f"  page {page}  {kind} {value}:  ...{ctx}...")

    print(
        f"\nNUMBER WORDS WITHOUT DIGITS ({len(report['number_words'])}): the extractor refuses these today"
    )
    for page, phrase, ctx in report["number_words"]:
        print(f"  page {page}  {phrase!r}:  ...{ctx}...")

    clean = all(p for _, p in report["required"]) and not report["unexpected"]
    print(
        "\nVERDICT:",
        "looks clean (still skim it)"
        if clean
        else "NEEDS A HUMAN LOOK before this contract is used",
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m data.tier_b.check_contract <case_id>   e.g. tb_01")
    main(sys.argv[1])
