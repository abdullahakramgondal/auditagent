"""Commercial set B: answer keys and writing prompts for harder invoices and purchase orders (TODO item 73).

Run:  python -m data.commercial_b.make_prompts
Then paste each prompt from data/commercial_b/prompts/ into Claude or ChatGPT (not Gemini, the model under
test), save the reply as data/commercial_b/documents/<id>.txt, print it to a PDF with a monospaced font
(for example Courier New) so that the columns stay in line, save the PDF as data/commercial_b/pdf/<id>.pdf
and check it with:  python -m data.commercial_b.check_document <id>
Freeze the documents in git BEFORE Agent 2 runs, run it ONCE, and never edit a document after seeing the
result. Every document has one shape that the generated documents of data/generator do not have.
Synthetic data only.
"""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

SET_DIR = Path(__file__).resolve().parent


def _row(name: str, quantity: int, unit_price: int) -> dict:
    """One item row of an answer key (money as text, the amount is quantity x unit price)."""
    return {
        "item_name": name,
        "quantity": quantity,
        "unit_price": str(unit_price),
        "line_total": str(quantity * unit_price),
    }


def _adjustment(label: str, amount: int) -> dict:
    """A line under the items: a negative amount is a deduction, a positive one is added."""
    return {"label": label, "amount": str(amount)}


def _total(rows: list[dict], adjustments: list[dict]) -> str:
    """The total of the rows and the adjustments, as text."""
    return str(sum(int(r["line_total"]) for r in rows) + sum(int(a["amount"]) for a in adjustments))


def _invoice(number, issued, delivered, due, rows, adjustments=()) -> dict:
    """The answer key of an invoice (the same keys as InvoiceData)."""
    adjustments = list(adjustments)
    return {
        "invoice_number": number,
        "invoice_date": issued,
        "delivery_date": delivered,
        "due_date": due,
        "line_items": rows,
        "adjustments": adjustments,
        "total_amount": _total(rows, adjustments),
    }


def _order(number, ordered, required, rows) -> dict:
    """The answer key of a purchase order (the same keys as PurchaseOrderData)."""
    return {
        "po_number": number,
        "po_date": ordered,
        "delivery_due_date": required,
        "line_items": rows,
        "total_amount": _total(rows, []),
    }


SPECS = [
    {
        "case_id": "cb_01",
        "kind": "invoice",
        "writer": "claude",
        "shape": "other labels (Tax Invoice No, Date of Supply, Payment Due By, Amount Payable)",
        "buyer": "Lahore Software House Pvt Ltd",
        "vendor": "Tech Supplies Pvt Ltd",
        "document": _invoice(
            "TI-2026-0417",
            "2026-11-03",
            "2026-10-30",
            "2026-12-03",
            [_row("Dell PowerEdge R650 Server", 3, 1250000)],
        ),
        "style_notes": [
            (
                "Use exactly these labels for the values: Tax Invoice No, Date of Issue, Date of Supply, "
                "Payment Due By and Amount Payable."
            )
        ],
    },
    {
        "case_id": "cb_02",
        "kind": "purchase_order",
        "writer": "chatgpt",
        "shape": "four item rows",
        "buyer": "Punjab Digital Solutions Pvt Ltd",
        "vendor": "Metro IT Distributors",
        "document": _order(
            "PO/IT/2026/0231",
            "2026-10-12",
            "2026-11-20",
            [
                _row("Cisco Catalyst 9200 Switch", 2, 480000),
                _row("Cisco SFP-10G-SR Transceiver", 8, 32500),
                _row("APC Smart-UPS 1500VA", 4, 118000),
                _row("Cat6 Patch Panel 24 Port", 6, 14500),
            ],
        ),
        "style_notes": ["The order has four item rows. Print each row on one line."],
    },
    {
        "case_id": "cb_03",
        "kind": "invoice",
        "writer": "claude",
        "shape": "discount written as a percentage line",
        "buyer": "Ravi Code Labs Pvt Ltd",
        "vendor": "Alpha Hardware Traders",
        "document": _invoice(
            "INV-77310",
            "2026-11-05",
            "2026-11-02",
            "2026-12-05",
            [_row("Lenovo ThinkCentre M70q Desktop", 25, 142000)],
            [_adjustment("Trade discount (5%)", -177500)],
        ),
        "style_notes": [
            (
                "Show the discount on its own line under the items, with exactly this label: "
                "Trade discount (5%), and the amount in PKR with a minus sign."
            )
        ],
    },
    {
        "case_id": "cb_04",
        "kind": "purchase_order",
        "writer": "chatgpt",
        "shape": "month-first and ordinal dates",
        "buyer": "Indus Cloud Services Pvt Ltd",
        "vendor": "Prime Network Solutions",
        "document": _order(
            "PO-2026-0788",
            "2026-10-12",
            "2026-11-20",
            [_row("Fortinet FortiGate 60F Firewall", 6, 215000)],
        ),
        "style_notes": [
            (
                'Write the order date as "October 12, 2026" (month first) and the required delivery '
                'date as "20th November 2026" (with an ordinal).'
            )
        ],
    },
    {
        "case_id": "cb_05",
        "kind": "invoice",
        "writer": "claude",
        "shape": "a sales tax line under the items",
        "buyer": "Five Rivers Technologies Pvt Ltd",
        "vendor": "Crescent Systems Pvt Ltd",
        "document": _invoice(
            "INV-2026-5521",
            "2026-11-10",
            "2026-11-08",
            "2026-12-10",
            [
                _row("HP ProBook 450 G10 Laptop", 10, 185000),
                _row("HP 65W Laptop Charger", 10, 4500),
            ],
            [_adjustment("Sales Tax (18%)", 341100)],
        ),
        "style_notes": [
            "Under the items print a line labelled Subtotal, then the tax line, then the total."
        ],
    },
    {
        "case_id": "cb_06",
        "kind": "purchase_order",
        "writer": "chatgpt",
        "shape": "an item name wrapped over two lines",
        "buyer": "Karakoram Software Pvt Ltd",
        "vendor": "Gulberg Computers",
        "document": _order(
            "PO-2026-0903",
            "2026-10-20",
            "2026-11-25",
            [_row("Samsung 32-inch 4K UHD Smart Monitor with Height-Adjustable Stand", 12, 58000)],
        ),
        "style_notes": [
            (
                "Print the item description over two lines: the first part of the description and the "
                "numbers on the first line, the rest of the description on the line below. Together the "
                "two lines must read as the exact item name given."
            )
        ],
    },
    {
        "case_id": "cb_07",
        "kind": "invoice",
        "writer": "claude",
        "shape": "payment terms (Net 30 days) instead of a due date",
        "buyer": "Hunza Cloud Pvt Ltd",
        "vendor": "Orbit Technology Traders",
        "document": _invoice(
            "SI-2026-0191",
            "2026-11-12",
            "2026-11-09",
            None,
            [_row("Ubiquiti UniFi Dream Machine Pro", 5, 78000)],
        ),
        "style_notes": ["Do not print a payment due date. State the terms as: Net 30 days."],
    },
    {
        "case_id": "cb_08",
        "kind": "invoice",
        "writer": "chatgpt",
        "shape": "quantity column first, amounts written as Rs.",
        "buyer": "Sialkot Data Systems Pvt Ltd",
        "vendor": "Eastern Networks Pvt Ltd",
        "document": _invoice(
            "KT-INV-3306",
            "2026-11-15",
            "2026-11-12",
            "2026-12-15",
            [
                _row("Cisco Meraki MX68 Security Appliance", 4, 325000),
                _row("Meraki 3-Year Enterprise License", 10, 42000),
            ],
        ),
        "style_notes": [
            (
                "In the items table put the quantity first, then the description, then the rate and "
                "the amount, and write every amount as Rs. instead of PKR (for example Rs. 42,000)."
            )
        ],
    },
]


def _date_text(iso: str) -> str:
    """A date as 3 November 2026."""
    d = date.fromisoformat(iso)
    return f"{d.day} {d:%B %Y}"


def _money(value) -> str:
    """Money as 1,250,000 (the answer keys hold whole rupees)."""
    return f"{int(Decimal(value)):,}"


def describe_document(spec: dict) -> list[str]:
    """The values the writer must print, one statement per value, from the answer key of a spec."""
    doc = spec["document"]
    if spec["kind"] == "invoice":
        lines = [
            f"Invoice number: {doc['invoice_number']} (write it exactly as given)",
            f"Invoice issue date: {_date_text(doc['invoice_date'])}",
            f"Delivery date: {_date_text(doc['delivery_date'])}"
            if doc["delivery_date"]
            else "No delivery date is printed.",
            f"Payment due date: {_date_text(doc['due_date'])}"
            if doc["due_date"]
            else "No payment due date is printed (see the notes).",
        ]
    else:
        lines = [
            f"Order number: {doc['po_number']} (write it exactly as given)",
            f"Order date: {_date_text(doc['po_date'])}",
            f"Required delivery date: {_date_text(doc['delivery_due_date'])}"
            if doc["delivery_due_date"]
            else "No required delivery date is printed.",
        ]
    for item in doc["line_items"]:
        lines.append(
            f"Item (write the name exactly as given): {item['item_name']}; quantity {item['quantity']}; "
            f"unit price PKR {_money(item['unit_price'])}; amount PKR {_money(item['line_total'])}"
        )
    adjustments = doc.get("adjustments", [])
    if adjustments:
        subtotal = sum(int(item["line_total"]) for item in doc["line_items"])
        lines.append(f"The items add up to PKR {subtotal:,} before the adjustments below.")
        for adjustment in adjustments:
            amount = int(adjustment["amount"])
            effect = "it is deducted: print it with a minus sign" if amount < 0 else "it is added"
            lines.append(
                f"Adjustment line under the items, labelled exactly '{adjustment['label']}', "
                f"amount PKR {abs(amount):,} ({effect})"
            )
    lines.append(f"Total: PKR {_money(doc['total_amount'])}")
    return lines


def build_prompt(spec: dict) -> str:
    """The prompt that asks a writer to print one document from the answer key of a spec."""
    kind_name = "invoice" if spec["kind"] == "invoice" else "purchase order"
    facts = "\n".join(f"- {line}" for line in describe_document(spec))
    notes = spec.get("style_notes", [])
    notes_block = ""
    if notes:
        notes_block = "\nNotes on how to print it\n" + "\n".join(f"- {n}" for n in notes) + "\n"
    return f"""Write the text of a {kind_name} from {spec["vendor"]} (the "Vendor") to {spec["buyer"]} (the "Buyer"), for IT equipment, as a Pakistani IT supplier would print it.

Format
- Plain text only: no markdown, no bold, no tables drawn with | or - characters.
- One page, about 15 to 30 lines. One line per item row: the description and the numbers on the same line, separated by at least two spaces, unless the notes say otherwise.
- Label every value with a natural label of your own choice; do not copy my wording. Dates may be written in any natural format unless the notes say otherwise.

Values that must each appear exactly once, exactly as given:
{facts}
{notes_block}
Everything else
- Do NOT add any other amount, tax, discount, fee, deposit, date or reference number. No phone numbers, NTN or bank account numbers. A footer line is allowed but must not contain numbers.

Output only the document text. No commentary, no placeholders such as [insert].
"""


def main() -> None:
    """Write the specs and the prompts of every document of the set."""
    for sub in ("specs", "prompts", "documents", "pdf"):
        (SET_DIR / sub).mkdir(exist_ok=True)
    for spec in SPECS:
        (SET_DIR / "specs" / f"{spec['case_id']}.json").write_text(
            json.dumps(spec, indent=2) + "\n"
        )
        (SET_DIR / "prompts" / f"{spec['case_id']}.txt").write_text(build_prompt(spec))
    print(f"wrote {len(SPECS)} specs and prompts in {SET_DIR}")


if __name__ == "__main__":
    main()
