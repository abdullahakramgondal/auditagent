import json
from decimal import Decimal
from pathlib import Path

from data.generator.ground_truth import evaluate_case

LATE_FLAT = {
    "clause_type": "late_penalty",
    "deadline": "2026-10-15",
    "mode": "flat_percent",
    "percent": "10",
}
VOLUME = {"clause_type": "volume_discount", "min_quantity": 50, "discount_percent": "5"}
PRICE = {"clause_type": "unit_price", "item_name": "Server", "agreed_unit_price": "1000000"}
TERMS = {"clause_type": "payment_terms", "net_days": 30}


def make_spec(rules, qty=10, price="1000000", total=None, due_date=None, vendor_applied=()):
    line_total = qty * Decimal(price)
    invoice = {
        "invoice_number": "INV-T",
        "invoice_date": "2026-10-26",
        "delivery_date": "2026-10-25",
        "line_items": [
            {
                "item_name": "Server",
                "quantity": qty,
                "unit_price": price,
                "line_total": str(line_total),
            }
        ],
        "total_amount": str(total if total is not None else line_total),
    }
    if due_date:
        invoice["due_date"] = due_date
    return {"rules": rules, "invoice": invoice, "vendor_applied": list(vendor_applied)}


def test_volume_discount_missed():
    out = evaluate_case(make_spec([VOLUME], qty=60))
    assert out["finding_types"] == ["volume_discount"]
    assert out["total_difference"] == Decimal(3000000)
    assert out["correct_payable"] == Decimal(57000000)


def test_volume_discount_applied_is_compliant():
    spec = make_spec([VOLUME], qty=60, total=57000000, vendor_applied=["volume_discount"])
    out = evaluate_case(spec)
    assert out["status"] == "COMPLIANT"
    assert out["total_difference"] == 0


def test_unit_price_overcharge():
    out = evaluate_case(make_spec([PRICE], price="1100000"))
    assert out["finding_types"] == ["unit_price"]
    assert out["total_difference"] == Decimal(1000000)


def test_payment_terms_breach():
    out = evaluate_case(make_spec([TERMS], due_date="2026-11-10"))
    assert out["status"] == "NON_COMPLIANT"
    assert out["finding_types"] == ["payment_terms"]
    assert out["total_difference"] == 0


def test_payment_terms_ok():
    out = evaluate_case(make_spec([TERMS], due_date="2026-11-25"))
    assert out["status"] == "COMPLIANT"


def test_combined_breaches_add_up():
    spec = make_spec([LATE_FLAT, VOLUME, PRICE], qty=60, price="1100000")
    out = evaluate_case(spec)
    # base = 60 x 1,000,000 = 60M; overcharge 6M; discount 3M; penalty 6M
    assert out["finding_types"] == ["late_penalty", "unit_price", "volume_discount"]
    assert out["correct_payable"] == Decimal(51000000)
    assert out["total_difference"] == Decimal(15000000)
    assert out["billed_total"] - out["correct_payable"] == out["total_difference"]


def test_case_001_matches_spec():
    path = Path(__file__).resolve().parents[2] / "data" / "specs" / "case_001.json"
    spec = json.loads(path.read_text())
    out = evaluate_case(spec)
    exp = spec["expected"]
    assert out["status"] == exp["status"]
    assert out["correct_payable"] == Decimal(exp["correct_payable"])
    assert out["total_difference"] == Decimal(exp["total_difference"])
    assert out["finding_types"] == exp["finding_types"]