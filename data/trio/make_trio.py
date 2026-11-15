"""Build a matched trio for one Tier B contract: a purchase order and an invoice that fit it.

Run:  python -m data.trio.make_trio tb_04            (writes the answer key and two prompts)
      python -m data.trio.make_trio tb_04 --clean    (an invoice that follows every rule)
      python -m data.trio.make_trio tb_04 --check    (reviews po.pdf and invoice.pdf against the key)
      python -m data.trio.make_trio tb_04 --expect   (prints the answer key again)

The contract is the written Tier B PDF. Paste each prompt of data/trio/<id>/prompts into Claude or
ChatGPT (not Gemini), save the reply in data/trio/<id>/documents, print it to PDF with a monospaced
font and save it as data/trio/<id>/po.pdf and data/trio/<id>/invoice.pdf. The answer key comes from
data/generator/ground_truth.py (never from the system under test). Synthetic data only.
Do not run this again for a trio that was already written: it would overwrite the prompts that were used.
"""

import argparse
import json
import shutil
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from auditagent.agents.doc_grounding import text_lines
from auditagent.ingestion.pdf_parser import parse_pdf
from data.commercial_b.check_document import review_text
from data.commercial_b.make_prompts import _invoice, _order, _row, build_prompt
from data.generator.ground_truth import evaluate_case
from data.tier_b.make_prompts import SPECS

TRIO_DIR = Path(__file__).resolve().parent
ROOT = TRIO_DIR.parents[1]
DEFAULT_ITEM = ("Dell PowerEdge R650 Server", 1250000)  # when the contract has no unit price rule
NO_LATE_RULE_DEADLINE = date(2026, 11, 15)


def build_trio(spec: dict, clean: bool = False) -> dict:
    """The purchase order, the invoice and the answer key that fit the rules of a Tier B spec.

    breach: every rule type of the contract is broken once (late, over the agreed price, a volume
    discount not given, a due date earlier than the terms allow). clean: the invoice follows every rule.
    """
    rules = {rule["clause_type"]: rule for rule in spec["rules"]}
    late, volume = rules.get("late_penalty"), rules.get("volume_discount")
    price_rule, terms = rules.get("unit_price"), rules.get("payment_terms")

    item, agreed = DEFAULT_ITEM
    if price_rule:
        item, agreed = price_rule["item_name"], int(float(price_rule["agreed_unit_price"]))
    quantity = 10
    if volume:
        quantity = int(volume["min_quantity"]) + (-1 if clean else 20)
    paid = agreed * 105 // 100 if price_rule and not clean else agreed

    deadline = date.fromisoformat(late["deadline"]) if late else NO_LATE_RULE_DEADLINE
    if late and not clean:
        extra = 4 if late["mode"] == "flat_percent" else 5
        delivered = deadline + timedelta(days=int(late.get("grace_days", 0)) + extra)
    else:
        delivered = deadline - timedelta(days=1)
    invoice_date = delivered + timedelta(days=3)
    net_days = int(terms["net_days"]) if terms else 30
    due = invoice_date + timedelta(days=net_days - (10 if terms and not clean else 0))

    digits = "".join(ch for ch in spec["case_id"] if ch.isdigit())
    order = _order(
        f"PO-2026-{digits}01",
        (deadline - timedelta(days=50)).isoformat(),
        deadline.isoformat(),
        [_row(item, quantity, agreed)],
    )
    invoice = _invoice(
        f"INV-2026-{digits}02",
        invoice_date.isoformat(),
        delivered.isoformat(),
        due.isoformat(),
        [_row(item, quantity, paid)],
    )
    expected = evaluate_case({"rules": spec["rules"], "invoice": invoice, "vendor_applied": []})
    return {"purchase_order": order, "invoice": invoice, "expected": expected}


def make_prompt(spec: dict, trio: dict, key: str) -> str:
    """The writing prompt of one document ("purchase_order" or "invoice").

    The prompt of commercial set B always says "from the Vendor to the Buyer", which is right for an
    invoice and wrong for a purchase order: a purchase order is issued by the Buyer to the Vendor.
    """
    buyer, vendor = spec["buyer"], spec["vendor"]
    text = build_prompt({"kind": key, "buyer": buyer, "vendor": vendor, "document": trio[key]})
    if key == "purchase_order":
        wrong = f'from {vendor} (the "Vendor") to {buyer} (the "Buyer")'
        right = f'from {buyer} (the "Buyer") to {vendor} (the "Vendor")'
        if wrong not in text:
            raise ValueError("the prompt of commercial set B changed: update make_prompt")
        text = text.replace(wrong, right, 1)
    return text


def money(value) -> str:
    return f"PKR {Decimal(str(value)):,.2f}"


def show_expected(expected: dict) -> None:
    print("\nANSWER KEY (from data/generator/ground_truth.py, not from the system)")
    print(f"  status           {expected['status']}")
    print(f"  billed total     {money(expected['billed_total'])}")
    print(f"  correct payable  {money(expected['correct_payable'])}")
    print(f"  overbilled       {money(expected['total_difference'])}")
    for kind, amount in expected["finding_amounts"].items():
        print(f"  finding          {kind}: {money(amount)}")


def write_trio(spec: dict, clean: bool, folder: Path) -> None:
    """Write the answer key, the two prompts and a copy of the contract PDF."""
    trio = build_trio(spec, clean)
    for sub in ("prompts", "documents"):
        (folder / sub).mkdir(parents=True, exist_ok=True)
    saved = {
        "case_id": spec["case_id"],
        "scenario": "clean" if clean else "breach",
        "buyer": spec["buyer"],
        "vendor": spec["vendor"],
        "rules": spec["rules"],
        **trio,
    }
    (folder / "spec.json").write_text(json.dumps(saved, indent=2, default=str) + "\n")
    for key, name in (("purchase_order", "po"), ("invoice", "invoice")):
        (folder / "prompts" / f"{name}.txt").write_text(make_prompt(spec, trio, key))
    source = ROOT / "data" / "tier_b" / "pdf" / f"{spec['case_id']}.pdf"
    if source.exists():
        shutil.copy(source, folder / "contract.pdf")
    else:
        print(f"WARNING: {source} is missing: copy the contract PDF to {folder / 'contract.pdf'}")
    print(f"wrote {folder}")
    rule_names = ", ".join(rule["clause_type"] for rule in spec["rules"])
    print(f"  contract: {spec['buyer']} and {spec['vendor']}, rules: {rule_names}")
    show_expected(trio["expected"])


def check(folder: Path, saved: dict) -> None:
    """Review po.pdf and invoice.pdf: is every required value there, and is anything extra?"""
    for kind, name in (("purchase_order", "po.pdf"), ("invoice", "invoice.pdf")):
        path = folder / name
        if not path.exists():
            print(f"\n{name}: MISSING (save it in {folder})")
            continue
        doc = parse_pdf(path)
        lines = text_lines("\n".join(page.text for page in doc.pages))
        report = review_text({"kind": kind, "document": saved[kind]}, lines)
        print(f"\n== {name}  pages: {doc.page_count}")
        if doc.page_count != 1:
            print("WARNING: more than one page: Agent 2 reads one page per document (item 74)")
        for label, evidence in report["required"]:
            print(f"  {'OK     ' if evidence else 'MISSING'} {label}")
        print(f"  unexpected amounts: {len(report['unexpected'])}")
        for line, token in report["unexpected"]:
            print(f"    {token}: {line}")
    contract = folder / "contract.pdf"
    if contract.exists():
        print(f"\ncontract.pdf: {parse_pdf(contract).page_count} pages")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("case_id", help="a Tier B case, for example tb_04")
    parser.add_argument("--clean", action="store_true", help="an invoice that follows every rule")
    parser.add_argument("--check", action="store_true", help="review po.pdf and invoice.pdf")
    parser.add_argument("--expect", action="store_true", help="print the answer key again")
    args = parser.parse_args()

    spec = next((s for s in SPECS if s["case_id"] == args.case_id), None)
    if spec is None:
        raise SystemExit(f"Unknown Tier B case: {args.case_id}")
    folder = TRIO_DIR / (args.case_id + ("_clean" if args.clean else ""))

    if args.check or args.expect:
        saved_path = folder / "spec.json"
        if not saved_path.exists():
            raise SystemExit(f"Run first without --check or --expect: {saved_path} is missing")
        saved = json.loads(saved_path.read_text())
        if args.expect:
            show_expected(saved["expected"])
        if args.check:
            check(folder, saved)
        return
    write_trio(spec, args.clean, folder)


if __name__ == "__main__":
    main()
