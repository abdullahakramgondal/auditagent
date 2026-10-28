"""Review a commercial_b document PDF against its answer key: are the required values there, and is anything extra?

Run:  python -m data.commercial_b.check_document cb_01
      python -m data.commercial_b.check_document cb_01 --text    (also print the text Agent 2 will read)
It reads data/commercial_b/pdf/<id>.pdf (exactly what Agent 2 will see) and data/commercial_b/specs/<id>.json.
The checks are looser than Agent 2's on purpose (a date may carry any label, an item name may wrap over
two lines), so a document can be fine here and still be refused by Agent 2: that is what the evaluation
measures. A human still decides: this only points at the places worth reading.
"""

import argparse
import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

from auditagent.agents.doc_grounding import (
    adjustment_problem,
    is_written,
    text_lines,
    total_is_written,
)
from auditagent.agents.grounding import date_in, number_in
from auditagent.ingestion.pdf_parser import normalize_for_match, parse_pdf

SET_DIR = Path(__file__).resolve().parent
_AMOUNT = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?")
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
NUMBER_KEY = {"invoice": "invoice_number", "purchase_order": "po_number"}
DATE_KEYS = {
    "invoice": ("invoice_date", "delivery_date", "due_date"),
    "purchase_order": ("po_date", "delivery_due_date"),
}


def _row_found(item: dict, lines: list[str]) -> bool:
    """True if the name, quantity, unit price and amount of an item are on one line or on two neighbouring lines.

    Every word of the name must be there, in any order, so a name that wraps over two lines is found.
    """
    words = normalize_for_match(item["item_name"]).lower().split()
    numbers = (item["quantity"], item["unit_price"], item["line_total"])
    for i, line in enumerate(lines):
        for text in (line, " ".join(lines[i : i + 2])):
            if all(word in text.lower() for word in words) and all(
                number_in(number, text) for number in numbers
            ):
                return True
    return False


def review_text(spec: dict, lines: list[str]) -> dict:
    """Pure function: required values found (with the line that holds them), unexpected amounts, lines with a year."""
    doc = spec["document"]
    number = doc[NUMBER_KEY[spec["kind"]]]
    required = [
        (f"number {number}", next((line for line in lines if is_written(number, [line])), None))
    ]
    for key in DATE_KEYS[spec["kind"]]:
        iso = doc.get(key)
        if iso:
            day = date.fromisoformat(iso)
            required.append(
                (f"{key} {iso}", next((line for line in lines if date_in(day, line)), None))
            )
    for item in doc["line_items"]:
        found = "item row found" if _row_found(item, lines) else None
        required.append((f"item {item['item_name']} x {item['quantity']}", found))
    for adjustment in doc.get("adjustments", []):
        problem = adjustment_problem(adjustment["label"], Decimal(adjustment["amount"]), lines)
        label = f"adjustment {adjustment['label']} {adjustment['amount']}"
        required.append((label, "label and amount on one line" if problem is None else None))
    total = Decimal(doc["total_amount"])
    required.append(
        (f"total {total}", "total line found" if total_is_written(total, lines) else None)
    )

    allowed = {total}
    subtotal = Decimal(0)
    for item in doc["line_items"]:
        allowed |= {Decimal(item["unit_price"]), Decimal(item["line_total"])}
        subtotal += Decimal(item["line_total"])
    allowed.add(subtotal)
    allowed |= {abs(Decimal(a["amount"])) for a in doc.get("adjustments", [])}
    unexpected = [
        (line, token)
        for line in lines
        for token in _AMOUNT.findall(line)
        if Decimal(token.replace(",", "")) not in allowed
    ]
    return {
        "required": required,
        "unexpected": unexpected,
        "date_lines": [line for line in lines if _YEAR.search(line)],
    }


def main(case_id: str, show_text: bool) -> None:
    """Print the review of one document."""
    spec = json.loads((SET_DIR / "specs" / f"{case_id}.json").read_text())
    doc = parse_pdf(SET_DIR / "pdf" / f"{case_id}.pdf")
    lines = text_lines("\n".join(page.text for page in doc.pages))
    report = review_text(spec, lines)

    print(f"== {case_id}  {spec['kind']}  writer: {spec.get('writer')}  pages: {doc.page_count}")
    print(f"shape: {spec.get('shape')}")
    if doc.page_count != 1:
        print("WARNING: more than one page, Agent 2 reads one page per document (TODO item 74)")
    if doc.warnings:
        print("parser warnings:", doc.warnings)

    print("\nREQUIRED VALUES")
    for label, evidence in report["required"]:
        mark = "OK     " if evidence else "MISSING"
        print(f"  {mark} {label}" + (f"   <- {evidence}" if evidence else ""))

    print(f"\nUNEXPECTED AMOUNTS ({len(report['unexpected'])}): is it a real extra charge?")
    for line, token in report["unexpected"]:
        print(f"  {token}:  {line}")

    print(
        f"\nLINES WITH A YEAR ({len(report['date_lines'])}): read them, a date must not be missing or extra"
    )
    for line in report["date_lines"]:
        print(f"  {line}")

    if show_text:
        print("\nTEXT")
        for line in lines:
            print(f"  | {line}")

    clean = all(evidence for _, evidence in report["required"]) and not report["unexpected"]
    print("\nVERDICT:", "looks clean (still skim it)" if clean else "NEEDS A HUMAN LOOK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("case_id", help="for example cb_01")
    parser.add_argument("--text", action="store_true", help="also print the text of the document")
    args = parser.parse_args()
    main(args.case_id, args.text)
