"""Tier B: answer keys (specs) and writing prompts for realistic, LLM-written contracts.

Run:  python -m data.tier_b.make_prompts
Then paste each prompt from data/tier_b/prompts/ into Claude or ChatGPT (not Gemini, which is the
model under test), save the reply as data/tier_b/contracts/<id>.txt, check it by hand, and export
it as a PDF. Synthetic data only.
"""

import json
from datetime import date
from pathlib import Path

TIER_DIR = Path(__file__).resolve().parent

DECOYS = [
    "A limitation of liability clause capping each party's liability at 10% of the total order value.",
    "A late payment charge of 2% per month that the Vendor may charge if the BUYER pays late.",
    "Termination by either party on thirty (30) days written notice.",
    "A warranty of twelve (12) months from delivery.",
]


def _late(deadline, mode, percent, cap=None, grace=0):
    rule = {"clause_type": "late_penalty", "deadline": deadline, "mode": mode,
            "percent": str(percent), "grace_days": grace}
    if cap is not None:
        rule["cap_percent"] = str(cap)
    return rule


def _volume(qty, pct):
    return {"clause_type": "volume_discount", "min_quantity": qty, "discount_percent": str(pct)}


def _price(item, price):
    return {"clause_type": "unit_price", "item_name": item, "agreed_unit_price": str(price)}


def _terms(days):
    return {"clause_type": "payment_terms", "net_days": days}


SPECS = [
    {"case_id": "tb_01", "writer": "claude", "buyer": "Lahore Software House Pvt Ltd", "vendor": "Tech Supplies Pvt Ltd",
     "rules": [_late("2026-11-20", "flat_percent", 8, grace=5), _terms(45)]},
    {"case_id": "tb_02", "writer": "chatgpt", "buyer": "Punjab Digital Solutions Pvt Ltd", "vendor": "Metro IT Distributors",
     "rules": [_late("2026-12-05", "per_day_percent", 1.5, cap=12), _volume(40, 6)]},
    {"case_id": "tb_03", "writer": "claude", "buyer": "Ravi Code Labs Pvt Ltd", "vendor": "Alpha Hardware Traders",
     "rules": [_price("Cisco Catalyst 9300 Switch", 540000), _terms(30), _volume(20, 4)]},
    {"case_id": "tb_04", "writer": "chatgpt", "buyer": "Indus Cloud Services Pvt Ltd", "vendor": "Prime Network Solutions",
     "rules": [_late("2026-10-31", "flat_percent", 10, grace=2), _volume(100, 12),
               _price("Lenovo ThinkPad T14 Laptop", 275000), _terms(60)]},
    {"case_id": "tb_05", "writer": "claude", "buyer": "Five Rivers Technologies Pvt Ltd", "vendor": "Crescent Systems Pvt Ltd",
     "rules": [_terms(21)]},
    {"case_id": "tb_06", "writer": "chatgpt", "buyer": "Lahore Software House Pvt Ltd", "vendor": "Metro IT Distributors",
     "rules": [_late("2027-01-15", "per_day_percent", 0.5, cap=5, grace=7),
               _price("HP LaserJet Enterprise Printer", 130000)]},
    {"case_id": "tb_07", "writer": "claude", "buyer": "Punjab Digital Solutions Pvt Ltd", "vendor": "Tech Supplies Pvt Ltd",
     "rules": [_volume(25, 3.5), _terms(14)]},
    {"case_id": "tb_08", "writer": "chatgpt", "buyer": "Ravi Code Labs Pvt Ltd", "vendor": "Prime Network Solutions",
     "rules": [_late("2026-12-31", "flat_percent", 15), _price("Fortinet FortiGate 100F Firewall", 620000),
               _volume(10, 2), _terms(30)]},
]


def _fmt_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {d:%B %Y}"


def _num(value) -> str:
    return format(float(value), "g")


def describe_rule(rule: dict) -> str:
    kind = rule["clause_type"]
    if kind == "late_penalty":
        when = _fmt_date(rule["deadline"])
        if rule["mode"] == "flat_percent":
            text = f"Late delivery penalty: if the Vendor delivers after {when}, a penalty of {_num(rule['percent'])}% of the invoice value applies (one single penalty)."
        else:
            text = (f"Late delivery penalty: for each day of delay after {when}, a penalty of {_num(rule['percent'])}% "
                    f"of the invoice value applies, up to a maximum total of {_num(rule['cap_percent'])}%.")
        if rule.get("grace_days"):
            text += f" The first {rule['grace_days']} days of delay carry no penalty."
        return text
    if kind == "volume_discount":
        return f"Volume discount: an order of {rule['min_quantity']} or more units in a single order receives a {_num(rule['discount_percent'])}% discount."
    if kind == "payment_terms":
        return f"Payment terms: each invoice must be paid within {rule['net_days']} days of the invoice date."
    return f"Agreed unit price: {rule['item_name']} at PKR {int(float(rule['agreed_unit_price'])):,} per unit; the invoice must not exceed it."


def build_prompt(spec: dict) -> str:
    terms = "\n".join(f"- {describe_rule(r)}" for r in spec["rules"])
    decoys = "\n".join(f"- {d}" for d in DECOYS)
    return f"""Write a realistic supply agreement between {spec['buyer']} (the "Buyer") and {spec['vendor']} (the "Vendor") for IT equipment, as it would appear in the procurement files of a Pakistani software company.

Length and style
- About 3,500 to 4,500 words, in formal legal English.
- Numbered clauses ("1.", "1.1", "2." and so on) with short headings. Include parties, definitions, term, scope of supply, delivery, price, payment, warranty, confidentiality, liability, termination, force majeure, governing law (Pakistan), notices and a signature block.
- Write every commercial term below in YOUR OWN natural legal wording, in the clause where it belongs. Do not copy my sentences. Write some numbers as words and digits together (for example "thirty (30) days") and others as digits only.

Commercial terms that must each appear exactly once, with exactly these values:
{terms}

Everything else
- Do NOT add any other penalty, discount, rebate, price, price list, fee, interest rate or payment deadline beyond the terms above and the decoy clauses below.
- Include these decoy clauses. They are ordinary boilerplate and must stay exactly as described:
{decoys}

Output only the contract text. No commentary, no markdown tables, no placeholders such as [insert].
"""


def main() -> None:
    for sub in ("specs", "prompts", "contracts", "pdf"):
        (TIER_DIR / sub).mkdir(exist_ok=True)
    for spec in SPECS:
        (TIER_DIR / "specs" / f"{spec['case_id']}.json").write_text(json.dumps(spec, indent=2) + "\n")
        (TIER_DIR / "prompts" / f"{spec['case_id']}.txt").write_text(build_prompt(spec))
    print(f"wrote {len(SPECS)} specs and prompts in {TIER_DIR}")


if __name__ == "__main__":
    main()