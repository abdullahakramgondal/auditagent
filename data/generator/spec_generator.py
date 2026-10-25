"""Generate the synthetic dataset specs: one recipe per category, driven by a seed."""

import json
import random
from datetime import date, timedelta
from pathlib import Path

from data.generator.commercial_pdf import DOC_VARIANTS
from data.generator.ground_truth import evaluate_case
from data.generator.templates import FILLERS, VARIANTS

ROOT = Path(__file__).resolve().parents[2]
SPEC_DIR = ROOT / "data" / "specs"

ALL_KINDS = ["late_penalty", "volume_discount", "unit_price", "payment_terms"]

CATEGORY_PLAN = [
    ("compliant_plain", 4),
    ("compliant_applied", 2),
    ("late_flat", 4),
    ("late_per_day", 4),
    ("grace_inside", 3),
    ("volume_missed", 3),
    ("price_over", 3),
    ("terms_wrong", 2),
    ("multi_breach", 3),
    ("decoy", 2),
]

# All names are fictional.
BUYERS = [
    "Lahore Software House Pvt Ltd",
    "Punjab Digital Solutions Pvt Ltd",
    "Ravi Code Labs Pvt Ltd",
    "Indus Cloud Services Pvt Ltd",
    "Five Rivers Technologies Pvt Ltd",
]
VENDORS = [
    "Tech Supplies Pvt Ltd",
    "Metro IT Distributors",
    "Alpha Hardware Traders",
    "Prime Network Solutions",
    "Crescent Systems Pvt Ltd",
]
# (name, min unit price, max unit price) in PKR, all multiples of 10,000
ITEMS = [
    ("Dell PowerEdge R750 Server", 1_200_000, 2_500_000),
    ("Cisco Catalyst 9300 Switch", 350_000, 700_000),
    ("Lenovo ThinkPad T14 Laptop", 220_000, 320_000),
    ("HP LaserJet Enterprise Printer", 90_000, 160_000),
    ("Fortinet FortiGate 100F Firewall", 400_000, 800_000),
    ("APC Smart-UPS 3000VA", 180_000, 300_000),
    ("Microsoft 365 Business License", 30_000, 40_000),
    ("Leased Line 100 Mbps (annual)", 900_000, 1_400_000),
]


def _late_rule(rng, deadline, mode, grace):
    rule = {
        "clause_type": "late_penalty",
        "deadline": deadline.isoformat(),
        "mode": mode,
        "grace_days": grace,
    }
    if mode == "flat_percent":
        rule["percent"] = str(rng.choice([5, 8, 10, 12, 15]))
    else:
        rule["percent"] = str(rng.choice([1, 2]))
        rule["cap_percent"] = str(rng.choice([5, 8, 10, 15]))
    return rule


def _plan(category, rng):
    """Return (kinds present in the contract, kinds breached, deductions the vendor applied)."""

    def with_extras(main):
        others = [k for k in ALL_KINDS if k != main]
        return [main] + rng.sample(others, rng.randint(0, 2))

    if category == "compliant_plain":
        return rng.sample(ALL_KINDS, rng.randint(2, 4)), set(), []
    if category == "compliant_applied":
        kind = rng.choice(["late_penalty", "volume_discount"])
        return [kind], set(), [kind]
    if category in ("late_flat", "late_per_day"):
        return with_extras("late_penalty"), {"late_penalty"}, []
    if category == "grace_inside":
        return with_extras("late_penalty"), set(), []
    if category == "volume_missed":
        return with_extras("volume_discount"), {"volume_discount"}, []
    if category == "price_over":
        return with_extras("unit_price"), {"unit_price"}, []
    if category == "terms_wrong":
        return with_extras("payment_terms"), {"payment_terms"}, []
    if category == "multi_breach":
        kinds = rng.sample(ALL_KINDS, rng.choice([2, 3]))
        return kinds, set(kinds), []
    if category == "decoy":
        return ["late_penalty"], {"late_penalty"}, []
    raise ValueError(f"Unknown category: {category}")


def _expected(result: dict) -> dict:
    return {
        "status": result["status"],
        "billed_total": str(result["billed_total"]),
        "correct_payable": str(result["correct_payable"]),
        "total_difference": str(result["total_difference"]),
        "finding_types": result["finding_types"],
        "finding_amounts": {k: str(v) for k, v in result["finding_amounts"].items()},
    }


def _line(item_name, quantity, price):
    return {
        "item_name": item_name,
        "quantity": quantity,
        "unit_price": str(price),
        "line_total": str(quantity * price),
    }


def build_spec(category: str, index: int) -> dict:
    seed = 1000 + index
    rng = random.Random(seed)
    kinds, breached, applied = _plan(category, rng)

    if category == "late_flat":
        mode, grace = "flat_percent", rng.choice([0, 0, 3])
    elif category == "late_per_day":
        mode, grace = "per_day_percent", rng.choice([0, 0, 3, 5])
    elif category == "grace_inside":
        mode, grace = rng.choice(["flat_percent", "per_day_percent"]), rng.choice([3, 5, 7])
    else:
        mode, grace = rng.choice(["flat_percent", "per_day_percent"]), rng.choice([0, 0, 3])

    po_date = date(2026, 8, 1) + timedelta(days=rng.randint(0, 45))
    deadline = po_date + timedelta(days=rng.randint(30, 60))

    name, lo, hi = rng.choice(ITEMS)
    agreed = rng.randrange(lo, hi + 1, 10_000)
    second = None
    if "volume_discount" not in kinds and rng.random() < 0.3:
        other = rng.choice([item for item in ITEMS if item[0] != name])
        second = (other[0], rng.randrange(other[1], other[2] + 1, 10_000), rng.randint(2, 15))

    rules = []
    qty = rng.randint(5, 40)
    offset = -rng.randint(0, 5)  # delivery relative to the deadline (negative = early)
    net_days = None
    paid = agreed

    for kind in kinds:
        if kind == "late_penalty":
            rules.append(_late_rule(rng, deadline, mode, grace))
            if "late_penalty" in breached or "late_penalty" in applied:
                offset = grace + rng.randint(1, 18)
            elif category == "grace_inside":
                offset = rng.randint(1, grace)
        elif kind == "volume_discount":
            min_q = rng.choice([20, 25, 30, 50])
            rules.append(
                {
                    "clause_type": "volume_discount",
                    "min_quantity": min_q,
                    "discount_percent": str(rng.choice([3, 5, 7, 10])),
                }
            )
            if "volume_discount" in breached or "volume_discount" in applied:
                qty = min_q + rng.randint(0, 25)
            else:
                qty = rng.randint(3, min_q - 1)
        elif kind == "unit_price":
            rules.append(
                {"clause_type": "unit_price", "item_name": name, "agreed_unit_price": str(agreed)}
            )
            if "unit_price" in breached:
                paid = agreed + agreed * rng.choice([5, 10, 15]) // 100
        else:
            net_days = rng.choice([15, 30, 45, 60])
            rules.append({"clause_type": "payment_terms", "net_days": net_days})

    delivery = deadline + timedelta(days=offset)
    invoice_date = delivery + timedelta(days=rng.randint(1, 5))
    due_date = None
    if net_days is not None:
        shift = -rng.randint(5, 12) if "payment_terms" in breached else rng.randint(0, 5)
        due_date = invoice_date + timedelta(days=net_days + shift)

    po_lines = [_line(name, qty, agreed)]
    inv_lines = [_line(name, qty, paid)]
    if second:
        po_lines.append(_line(second[0], second[2], second[1]))
        inv_lines.append(_line(second[0], second[2], second[1]))
    po_total = sum(int(x["line_total"]) for x in po_lines)
    lines_total = sum(int(x["line_total"]) for x in inv_lines)

    pages = rng.randint(3, 5) if category == "decoy" else rng.randint(3, 20)
    if category == "decoy":
        fillers = ["liability", "late_payment_charge"] + rng.sample(
            ["confidentiality", "termination", "warranty"], 1
        )
    else:
        fillers = rng.sample(list(FILLERS), rng.randint(2, 5))

    invoice = {
        "invoice_number": f"INV-{5000 + index}",
        "invoice_date": invoice_date.isoformat(),
        "delivery_date": delivery.isoformat(),
        "line_items": inv_lines,
        "total_amount": str(lines_total),
        "adjustments": [],
    }
    if due_date:
        invoice["due_date"] = due_date.isoformat()

    spec = {
        "case_id": f"gen_{index:03d}",
        "category": category,
        "seed": seed,
        "buyer": rng.choice(BUYERS),
        "vendor": rng.choice(VENDORS),
        "layout": {
            "contract_pages": pages,
            "wording_variant": rng.choice(VARIANTS),
            "doc_variant": random.Random(seed + 7).choice(DOC_VARIANTS),
            "filler_clauses": fillers,
            "target_page": {r["clause_type"]: rng.randint(2, pages) for r in rules},
        },
        "rules": rules,
        "purchase_order": {
            "po_number": f"PO-2026-{100 + index}",
            "po_date": po_date.isoformat(),
            "delivery_due_date": deadline.isoformat(),
            "line_items": po_lines,
            "total_amount": str(po_total),
        },
        "invoice": invoice,
        "vendor_applied": [],
    }

    if applied:
        full = evaluate_case(spec)["finding_amounts"]  # nothing applied yet: full amounts
        labels = {
            "late_penalty": "Less: late delivery penalty",
            "volume_discount": "Less: volume discount",
        }
        adjustments = []
        for kind in applied:
            if kind not in full:
                raise ValueError(f"{spec['case_id']}: nothing to apply for {kind}")
            adjustments.append({"label": labels[kind], "amount": str(-int(full[kind]))})
        invoice["adjustments"] = adjustments
        invoice["total_amount"] = str(lines_total + sum(int(a["amount"]) for a in adjustments))
        spec["vendor_applied"] = list(applied)

    spec["expected"] = _expected(evaluate_case(spec))
    return spec


def generate_all() -> list[dict]:
    specs, index = [], 0
    for category, count in CATEGORY_PLAN:
        for _ in range(count):
            index += 1
            specs.append(build_spec(category, index))
    return specs


def write_specs(spec_dir=SPEC_DIR) -> int:
    spec_dir = Path(spec_dir)
    spec_dir.mkdir(parents=True, exist_ok=True)
    specs = generate_all()
    for spec in specs:
        (spec_dir / f"{spec['case_id']}.json").write_text(json.dumps(spec, indent=2) + "\n")
    return len(specs)


def main() -> None:
    print(f"wrote {write_specs()} specs to {SPEC_DIR}")


if __name__ == "__main__":
    main()