"""Render purchase order and invoice specs into one-page PDFs (three layouts)."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from data.generator.templates import fmt_date, fmt_pkr

PAGE_W, PAGE_H = A4
MARGIN = 56
COLS = (MARGIN, 280, 340, 440)  # item, qty, unit price, amount
RIGHT_X = 300  # second header column in layout 2
MAX_ITEM_CHARS = 38
DOC_VARIANTS = (1, 2, 3)
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

TITLES = {
    "invoice": {1: "INVOICE", 2: "SALES INVOICE", 3: "INVOICE"},
    "po": {1: "PURCHASE ORDER", 2: "ORDER FORM", 3: "PURCHASE ORDER"},
}
LABELS = {
    "invoice": {
        1: {"number": "Invoice No", "date": "Invoice Date", "delivery": "Delivery Date",
            "due": "Due Date", "buyer": "Bill To", "vendor": "From", "total": "Total"},
        2: {"number": "Bill No", "date": "Bill Date", "delivery": "Delivered On",
            "due": "Payment Due", "buyer": "Customer", "vendor": "Supplier", "total": "Total Payable"},
        3: {"number": "Invoice #", "date": "Issued On", "delivery": "Date of Delivery",
            "due": "Pay By", "buyer": "Billed To", "vendor": "Vendor", "total": "Grand Total"},
    },
    "po": {
        1: {"number": "PO No", "date": "PO Date", "due": "Delivery Due Date",
            "buyer": "Buyer", "vendor": "Vendor", "total": "Total"},
        2: {"number": "Order No", "date": "Order Date", "due": "Required By",
            "buyer": "Ordered By", "vendor": "Supplier", "total": "Total Payable"},
        3: {"number": "Purchase Order #", "date": "Raised On", "due": "Deliver By",
            "buyer": "Issued By", "vendor": "To", "total": "Grand Total"},
    },
}
COLUMN_HEADERS = {
    1: ("Item", "Qty", "Unit Price (PKR)", "Amount (PKR)"),
    2: ("Description", "Units", "Rate (PKR)", "Total (PKR)"),
}


def fmt_doc_date(iso: str, variant: int) -> str:
    d = date.fromisoformat(iso)
    if variant == 1:
        return fmt_date(d)
    if variant == 2:
        return f"{d.day:02d}-{MONTHS[d.month - 1]}-{d.year}"
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


def _money(value) -> str:
    return f"{Decimal(str(value)):,.0f}"


def _variant(spec: dict) -> int:
    variant = spec.get("layout", {}).get("doc_variant", 1)
    if variant not in DOC_VARIANTS:
        raise ValueError(f"Unknown doc_variant: {variant}")
    return variant


def _draw_document(path, variant, title, header, items, total, total_label, adjustments=()) -> Path:
    """header is a list of (side, label, value); side is 'main' or 'party'."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=A4)

    y = PAGE_H - MARGIN
    c.setFont("Helvetica-Bold", 16)
    c.drawString(MARGIN, y, title)
    y -= 34

    c.setFont("Helvetica", 11)
    if variant == 2:
        y_left, y_right = y, y
        for side, label, value in header:
            if side == "main":
                c.drawString(MARGIN, y_left, f"{label}: {value}")
                y_left -= 16
            else:
                c.drawString(RIGHT_X, y_right, f"{label}: {value}")
                y_right -= 16
        y = min(y_left, y_right)
    else:
        for _, label, value in header:
            c.drawString(MARGIN, y, f"{label}: {value}")
            y -= 16
    y -= 14

    if variant == 3:
        for number, it in enumerate(items, start=1):
            if len(it["item_name"]) > MAX_ITEM_CHARS:
                raise ValueError(f"Item name too long: {it['item_name']}")
            c.drawString(MARGIN, y, f"{number}. {it['item_name']}")
            y -= 15
            c.drawString(
                MARGIN + 18,
                y,
                f"{it['quantity']} x {fmt_pkr(it['unit_price'])} = {fmt_pkr(it['line_total'])}",
            )
            y -= 20
            if y < MARGIN + 60:
                raise ValueError("Too many line items for one page")
        for adj in adjustments:
            amount = Decimal(str(adj["amount"]))
            sign = "-" if amount < 0 else ""
            c.drawString(MARGIN, y, f"{adj['label']}: {sign}{fmt_pkr(abs(amount))}")
            y -= 16
        y -= 10
        c.setFont("Helvetica-Bold", 12)
        c.drawString(MARGIN, y, f"{total_label}: {fmt_pkr(total)}")
    else:
        c.setFont("Helvetica-Bold", 11)
        for x, label in zip(COLS, COLUMN_HEADERS[variant]):
            c.drawString(x, y, label)
        y -= 18

        c.setFont("Helvetica", 11)
        for it in items:
            if len(it["item_name"]) > MAX_ITEM_CHARS:
                raise ValueError(f"Item name too long: {it['item_name']}")
            c.drawString(COLS[0], y, it["item_name"])
            c.drawString(COLS[1], y, str(it["quantity"]))
            c.drawString(COLS[2], y, _money(it["unit_price"]))
            c.drawString(COLS[3], y, _money(it["line_total"]))
            y -= 16
            if y < MARGIN + 60:
                raise ValueError("Too many line items for one page")
        for adj in adjustments:
            amount = Decimal(str(adj["amount"]))
            sign = "-" if amount < 0 else ""
            c.drawString(COLS[0], y, adj["label"])
            c.drawString(COLS[3], y, f"{sign}{_money(abs(amount))}")
            y -= 16
        y -= 10
        c.setFont("Helvetica-Bold", 12)
        c.drawString(COLS[2], y, f"{total_label}:")
        c.drawString(COLS[3], y, fmt_pkr(total))

    c.showPage()
    c.save()
    return path


def write_po_pdf(spec: dict, out_path) -> Path:
    po = spec["purchase_order"]
    variant = _variant(spec)
    lab = LABELS["po"][variant]
    header = [
        ("main", lab["number"], po["po_number"]),
        ("main", lab["date"], fmt_doc_date(po["po_date"], variant)),
    ]
    if po.get("delivery_due_date"):
        header.append(("main", lab["due"], fmt_doc_date(po["delivery_due_date"], variant)))
    header += [("party", lab["buyer"], spec["buyer"]), ("party", lab["vendor"], spec["vendor"])]
    return _draw_document(
        out_path, variant, TITLES["po"][variant], header,
        po["line_items"], po["total_amount"], lab["total"],
    )


def write_invoice_pdf(spec: dict, out_path) -> Path:
    inv = spec["invoice"]
    variant = _variant(spec)
    lab = LABELS["invoice"][variant]
    header = [
        ("main", lab["number"], inv["invoice_number"]),
        ("main", lab["date"], fmt_doc_date(inv["invoice_date"], variant)),
    ]
    if inv.get("delivery_date"):
        header.append(("main", lab["delivery"], fmt_doc_date(inv["delivery_date"], variant)))
    if inv.get("due_date"):
        header.append(("main", lab["due"], fmt_doc_date(inv["due_date"], variant)))
    header += [("party", lab["buyer"], spec["buyer"]), ("party", lab["vendor"], spec["vendor"])]
    return _draw_document(
        out_path, variant, TITLES["invoice"][variant], header,
        inv["line_items"], inv["total_amount"], lab["total"],
        inv.get("adjustments", []),
    )