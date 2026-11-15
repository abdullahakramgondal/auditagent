"""Show the rule engine alone on one generated case: no model, no network.

Run:  python -m eval.show_case gen_007
The rules and the invoice come from the spec (what a perfect Agent 1 and Agent 2 would return);
only the Python rule engine computes the result, and it is compared with the answer key.
"""

import json
import sys
from decimal import Decimal
from pathlib import Path

from auditagent.rules.engine import audit_invoice
from auditagent.schemas.contract import ExtractedContract
from auditagent.schemas.invoice import InvoiceData

ROOT = Path(__file__).resolve().parents[1]


def pkr(value) -> str:
    return f"PKR {Decimal(str(value)):,.2f}"


def main(case_id: str) -> None:
    spec = json.loads((ROOT / "data" / "specs" / f"{case_id}.json").read_text())
    note = {"page": 1, "text": "(Agent 1 copies the clause text from the PDF)"}
    contract = ExtractedContract.model_validate(
        {"rules": [{**rule, "source": note} for rule in spec["rules"]]}
    )
    invoice = InvoiceData.model_validate(spec["invoice"])

    print(f"CASE {case_id}  ({spec.get('category', 'hand-made')})")
    print("\nRULES IN THE CONTRACT (what Agent 1 reads)")
    for rule in spec["rules"]:
        print("  ", {k: v for k, v in rule.items() if k != "clause_type"}, rule["clause_type"])
    print("\nTHE INVOICE (what Agent 2 reads)")
    print(
        f"   delivered {invoice.delivery_date}, invoice date {invoice.invoice_date}, "
        f"due {invoice.due_date}"
    )
    for item in invoice.line_items:
        print(f"   {item.item_name}: {item.quantity} x {pkr(item.unit_price)}")
    for adjustment in invoice.adjustments:
        print(f"   {adjustment.label}: {pkr(adjustment.amount)}")
    print(f"   billed total {pkr(invoice.total_amount)}")

    result = audit_invoice(contract, invoice)
    print(f"\nTHE RULE ENGINE (plain Python): {result.status}")
    print(f"   billed total     {pkr(result.billed_total)}")
    print(f"   correct payable  {pkr(result.correct_payable)}")
    print(f"   overbilled       {pkr(result.total_difference)}")
    for finding in result.findings:
        print(f"   - [{finding.clause_type}] {pkr(finding.difference)}: {finding.description}")
    for reason in result.review_reasons:
        print(f"   - REVIEW: {reason}")

    expected = spec["expected"]
    match = (
        result.status == expected["status"]
        and result.correct_payable == Decimal(expected["correct_payable"])
        and result.total_difference == Decimal(expected["total_difference"])
    )
    print(
        f"\nANSWER KEY: {expected['status']}, correct payable {pkr(expected['correct_payable'])}, "
        f"overbilled {pkr(expected['total_difference'])}"
    )
    print("THE ENGINE MATCHES THE ANSWER KEY" if match else "DIFFERENT FROM THE ANSWER KEY")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m eval.show_case <case_id>   e.g. gen_007")
    main(sys.argv[1])
