"""Show the text around a word in a Tier B PDF.

Run:  python -m data.tier_b.show_around tb_03 discount
"""

import sys
from pathlib import Path

from auditagent.ingestion.pdf_parser import normalize_for_match, parse_pdf

TIER_DIR = Path(__file__).resolve().parent


def main(case_id: str, word: str, width: int = 260) -> None:
    doc = parse_pdf(TIER_DIR / "pdf" / f"{case_id}.pdf")
    hits = 0
    for page in doc.pages:
        text = normalize_for_match(page.text)
        low, start = text.lower(), 0
        while (i := low.find(word.lower(), start)) >= 0:
            hits += 1
            print(f"page {page.number}: ...{text[max(0, i - width) : i + width]}...\n")
            start = i + len(word) + width  # skip hits that overlap the one just shown
    print(f"{hits} place(s) found")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python -m data.tier_b.show_around <case_id> <word>")
    main(sys.argv[1], sys.argv[2])
