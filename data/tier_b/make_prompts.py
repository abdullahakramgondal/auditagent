"""Tier B: answer keys (specs) and writing prompts for realistic, LLM-written contracts.

Run:  python -m data.tier_b.make_prompts
Then paste each prompt from data/tier_b/prompts/ into Claude or ChatGPT (not Gemini, which is the
model under test), save the reply as data/tier_b/contracts/<id>.txt, check it by hand, and export
it as a PDF. Synthetic data only.

A spec may carry three optional keys:
  style_notes    extra instructions on HOW the writer words the terms
  extra_decoys   extra boilerplate clauses with numbers that are NOT rules
  decoy_numbers  the numbers in those extra decoys, {"percent": [...], "days": [...]}, so that
                 check_contract does not report them as unexpected rules
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
    rule = {
        "clause_type": "late_penalty",
        "deadline": deadline,
        "mode": mode,
        "percent": str(percent),
        "grace_days": grace,
    }
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
    {
        "case_id": "tb_01",
        "writer": "claude",
        "buyer": "Lahore Software House Pvt Ltd",
        "vendor": "Tech Supplies Pvt Ltd",
        "rules": [_late("2026-11-20", "flat_percent", 8, grace=5), _terms(45)],
    },
    {
        "case_id": "tb_02",
        "writer": "chatgpt",
        "buyer": "Punjab Digital Solutions Pvt Ltd",
        "vendor": "Metro IT Distributors",
        "rules": [_late("2026-12-05", "per_day_percent", 1.5, cap=12), _volume(40, 6)],
    },
    {
        "case_id": "tb_03",
        "writer": "claude",
        "buyer": "Ravi Code Labs Pvt Ltd",
        "vendor": "Alpha Hardware Traders",
        "rules": [_price("Cisco Catalyst 9300 Switch", 540000), _terms(30), _volume(20, 4)],
    },
    {
        "case_id": "tb_04",
        "writer": "chatgpt",
        "buyer": "Indus Cloud Services Pvt Ltd",
        "vendor": "Prime Network Solutions",
        "rules": [
            _late("2026-10-31", "flat_percent", 10, grace=2),
            _volume(100, 12),
            _price("Lenovo ThinkPad T14 Laptop", 275000),
            _terms(60),
        ],
    },
    {
        "case_id": "tb_05",
        "writer": "claude",
        "buyer": "Five Rivers Technologies Pvt Ltd",
        "vendor": "Crescent Systems Pvt Ltd",
        "rules": [_terms(21)],
    },
    {
        "case_id": "tb_06",
        "writer": "chatgpt",
        "buyer": "Lahore Software House Pvt Ltd",
        "vendor": "Metro IT Distributors",
        "rules": [
            _late("2027-01-15", "per_day_percent", 0.5, cap=5, grace=7),
            _price("HP LaserJet Enterprise Printer", 130000),
        ],
    },
    {
        "case_id": "tb_07",
        "writer": "claude",
        "buyer": "Punjab Digital Solutions Pvt Ltd",
        "vendor": "Tech Supplies Pvt Ltd",
        "rules": [_volume(25, 3.5), _terms(14)],
    },
    {
        "case_id": "tb_08",
        "writer": "chatgpt",
        "buyer": "Ravi Code Labs Pvt Ltd",
        "vendor": "Prime Network Solutions",
        "rules": [
            _late("2026-12-31", "flat_percent", 15),
            _price("Fortinet FortiGate 100F Firewall", 620000),
            _volume(10, 2),
            _terms(30),
        ],
    },
    # tb_09 to tb_12: written on Day 14. They were looked at while fixing Agent 1, so they are no
    # longer an untouched set.
    {
        "case_id": "tb_09",
        "writer": "claude",
        "buyer": "Karakoram Software Pvt Ltd",
        "vendor": "Gulberg Computers",
        "rules": [
            _late("2027-02-28", "per_day_percent", 2.5, cap=15, grace=4),
            _volume(30, 7),
            _price("Dell UltraSharp U2723QE Monitor", 85000),
            _terms(28),
        ],
        "style_notes": [
            (
                "Late delivery penalty: do not write the delivery date inside the penalty clause. "
                "Write it once, in the delivery clause, as a defined term of your own choice (a "
                "capitalised term in quotation marks and brackets), and in the penalty clause refer "
                "to the date only by that term."
            ),
        ],
        "extra_decoys": [
            (
                "The Buyer shall inspect the Equipment within seven (7) days of delivery; Equipment "
                "not rejected in writing within that period is deemed accepted."
            ),
            (
                "A restocking fee of 5% of the price of the returned goods applies to undamaged "
                "Equipment that the Buyer asks to return after acceptance."
            ),
        ],
        "decoy_numbers": {"percent": [5], "days": [7]},
    },
    {
        "case_id": "tb_10",
        "writer": "chatgpt",
        "buyer": "Sialkot Data Systems Pvt Ltd",
        "vendor": "Eastern Networks Pvt Ltd",
        "rules": [_late("2027-03-15", "flat_percent", 6), _volume(15, 4.5), _terms(45)],
        "style_notes": [
            (
                'Volume discount: do not use the word "discount" for this term. Call it a reduction, '
                "a rebate or another natural name of your own choice."
            ),
        ],
        "extra_decoys": [
            (
                "Early payment discount: the Vendor shall allow the Buyer a discount of 1.5% on any "
                "invoice that the Buyer pays within seven (7) days of the invoice date."
            ),
        ],
        "decoy_numbers": {"percent": [1.5], "days": [7]},
    },
    {
        "case_id": "tb_11",
        "writer": "claude",
        "buyer": "Margalla Analytics Pvt Ltd",
        "vendor": "Zenith Hardware Pvt Ltd",
        "rules": [_price("Ubiquiti UniFi 6 Enterprise Access Point", 38500), _terms(35)],
        "extra_decoys": [
            (
                "Support response: the Vendor shall respond to each support request within four (4) "
                "business hours; for each full day of delay in responding, the Buyer is entitled to a "
                "service credit of 3% of the monthly support fee."
            ),
        ],
        "decoy_numbers": {"percent": [3], "days": []},
    },
    {
        "case_id": "tb_12",
        "writer": "chatgpt",
        "buyer": "Hunza Cloud Pvt Ltd",
        "vendor": "Orbit Technology Traders",
        "rules": [
            _late("2027-04-30", "per_day_percent", 1, cap=8, grace=3),
            _volume(50, 5),
            _price("Samsung 990 PRO 2TB NVMe SSD", 62000),
            _terms(25),
        ],
        "style_notes": [
            (
                "Late delivery penalty: write the delivery date, the grace period and the penalty "
                "percentage with its maximum in three separate, neighbouring sentences of one clause."
            ),
            (
                "Agreed unit price: state the price in one sentence and, in a separate sentence of "
                "the same clause, say that the price is fixed for the term of the agreement and can "
                "only change by written amendment."
            ),
        ],
        "extra_decoys": [
            (
                "The Buyer may reject non-conforming Equipment by written notice within fifteen (15) "
                "days of delivery."
            ),
        ],
        "decoy_numbers": {"percent": [], "days": [15]},
    },
    # tb_13 to tb_16: the next untouched set (TODO item 58). Freeze the contracts in git, run Agent 1
    # on them ONCE, and never edit a contract after seeing the result. tb_14 is expected to be
    # refused today: a cross-reference to the date clause is not a link Agent 1 can prove yet.
    {
        "case_id": "tb_13",
        "writer": "claude",
        "buyer": "Cholistan Tech Solutions Pvt Ltd",
        "vendor": "Defence Road Electronics",
        "rules": [
            _late("2027-05-14", "flat_percent", 12, grace=6),
            _volume(60, 8),
            _terms(40),
        ],
        "style_notes": [
            (
                "Late delivery penalty: do not write the delivery date inside the penalty clause. "
                'Write it only in the definitions clause, in the form "Term" means <date>, using a '
                "capitalised term of your own choice, and in the penalty clause refer to the date "
                "only by that term."
            ),
            (
                "Payment terms: write the period as a net period, for example Net 40, and not as "
                '"within 40 days".'
            ),
        ],
        "extra_decoys": [
            (
                "The Vendor shall acknowledge each purchase order in writing within fourteen (14) "
                "days of receiving it."
            ),
        ],
        "decoy_numbers": {"percent": [], "days": [14]},
    },
    {
        "case_id": "tb_14",
        "writer": "chatgpt",
        "buyer": "Jhelum Digital Pvt Ltd",
        "vendor": "Citadel IT Supplies",
        "rules": [
            _late("2027-06-10", "per_day_percent", 0.75, cap=6),
            _price("Dell Latitude 5440 Laptop", 148000),
            _terms(50),
        ],
        "style_notes": [
            (
                "Late delivery penalty: write the delivery date once, in the delivery clause, and do "
                "not define a term for it. In the penalty clause refer to it only by a cross-reference "
                'such as "the date stated in clause 5.2" (use the real clause number).'
            ),
        ],
        "extra_decoys": [
            (
                "If the Buyer cancels a confirmed order within five (5) days before the scheduled "
                "delivery, a cancellation charge of 4% of the order value is payable by the Buyer."
            ),
        ],
        "decoy_numbers": {"percent": [4], "days": [5]},
    },
    {
        "case_id": "tb_15",
        "writer": "claude",
        "buyer": "Kalam Systems Pvt Ltd",
        "vendor": "Pioneer Network Traders",
        "rules": [
            _price("Cisco Meraki MR46 Access Point", 92000),
            _volume(20, 3),
            _terms(15),
        ],
        "style_notes": [
            (
                "Agreed unit price: do not state the price in the price clause. State it only in a "
                "Price Schedule headed Schedule 1, placed after the last numbered clause and before "
                "the signature block, as plain lines in the form Item: <name> and Unit price: PKR "
                "<amount> per unit. In the price clause say only that unit prices are set out in "
                "Schedule 1 and that an invoice shall not exceed them."
            ),
        ],
        "extra_decoys": [
            (
                "The Vendor shall replace defective Equipment within five (5) days of written "
                "notice from the Buyer."
            ),
        ],
        "decoy_numbers": {"percent": [], "days": [5]},
    },
    {
        "case_id": "tb_16",
        "writer": "chatgpt",
        "buyer": "Nawaz Cloud Technologies Pvt Ltd",
        "vendor": "Summit Hardware Pvt Ltd",
        "rules": [
            _late("2027-07-31", "flat_percent", 7.5),
            _volume(35, 6.5),
            _terms(55),
        ],
        "style_notes": [
            (
                "Late delivery penalty: call it liquidated damages and do not use the word "
                '"penalty" for this term.'
            ),
            (
                'Volume discount: do not use the words "discount", "rebate" or "reduction" for this '
                "term. Call it a price adjustment, a credit or another natural name of your own "
                "choice."
            ),
        ],
        "extra_decoys": [
            (
                "The Buyer may withhold 5% of the value of each invoice as retention until "
                "acceptance testing of the Equipment has been completed."
            ),
        ],
        "decoy_numbers": {"percent": [5], "days": []},
    },
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
            text = (
                f"Late delivery penalty: for each day of delay after {when}, a penalty of {_num(rule['percent'])}% "
                f"of the invoice value applies, up to a maximum total of {_num(rule['cap_percent'])}%."
            )
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
    decoys = "\n".join(f"- {d}" for d in DECOYS + spec.get("extra_decoys", []))
    notes = spec.get("style_notes", [])
    notes_block = ""
    if notes:
        notes_block = "\nHow to write these terms\n" + "\n".join(f"- {n}" for n in notes) + "\n"
    return f"""Write a realistic supply agreement between {spec["buyer"]} (the "Buyer") and {spec["vendor"]} (the "Vendor") for IT equipment, as it would appear in the procurement files of a Pakistani software company.

Length and style
- About 3,500 to 4,500 words, in formal legal English.
- Numbered clauses ("1.", "1.1", "2." and so on) with short headings. Include parties, definitions, term, scope of supply, delivery, price, payment, warranty, confidentiality, liability, termination, force majeure, governing law (Pakistan), notices and a signature block.
- Write every commercial term below in YOUR OWN natural legal wording, in the clause where it belongs. Do not copy my sentences. Write some numbers as words and digits together (for example "thirty (30) days") and others as digits only.

Commercial terms that must each appear exactly once, with exactly these values:
{terms}
{notes_block}
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
        (TIER_DIR / "specs" / f"{spec['case_id']}.json").write_text(
            json.dumps(spec, indent=2) + "\n"
        )
        (TIER_DIR / "prompts" / f"{spec['case_id']}.txt").write_text(build_prompt(spec))
    print(f"wrote {len(SPECS)} specs and prompts in {TIER_DIR}")


if __name__ == "__main__":
    main()
