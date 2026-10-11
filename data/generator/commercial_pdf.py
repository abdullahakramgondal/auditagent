"""Render purchase order and invoice specs into one-page PDFs."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from data.generator.templates import fmt_date, fmt_pkr

PAGE_W, PAGE_H = A4
MARGIN = 56
COLS = (MARGIN, 280, 340, 440)  # item, qty, unit price, amount
MAX_ITEM_CHARS = 38


def _money(value) -> str:
    return f"{Decimal(str(value)):,.0f}"


def _date_line(label: str, iso: str | None) -> list[str]:
    return [f"{label}: {fmt_date(date.fromisoformat(iso))}"] if iso else []


def _draw_document(path, title, header_lines, items, total, adjustments=()) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=A4)

    y = PAGE_H - MARGIN
    c.setFont("Helvetica-Bold", 16)
    c.drawString(MARGIN, y, title)
    y -= 34

    c.setFont("Helvetica", 11)
    for line in header_lines:
        c.drawString(MARGIN, y, line)
        y -= 16
    y -= 14

    c.setFont("Helvetica-Bold", 11)
    for x, label in zip(COLS, ("Item", "Qty", "Unit Price (PKR)", "Amount (PKR)")):
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
        if y < MARGIN + 40:
            raise ValueError("Too many line items for one page")

    for adj in adjustments:
        amount = Decimal(str(adj["amount"]))
        sign = "-" if amount < 0 else ""
        c.drawString(COLS[0], y, adj["label"])
        c.drawString(COLS[3], y, f"{sign}{_money(abs(amount))}")
        y -= 16

    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(COLS[2], y, "Total:")
    c.drawString(COLS[3], y, fmt_pkr(total))
    c.showPage()
    c.save()
    return path


def write_po_pdf(spec: dict, out_path) -> Path:
    po = spec["purchase_order"]
    header = [f"PO No: {po['po_number']}"]
    header += _date_line("PO Date", po["po_date"])
    header += _date_line("Delivery Due Date", po.get("delivery_due_date"))
    header += [f"Buyer: {spec['buyer']}", f"Vendor: {spec['vendor']}"]
    return _draw_document(out_path, "PURCHASE ORDER", header, po["line_items"], po["total_amount"])


def write_invoice_pdf(spec: dict, out_path) -> Path:
    inv = spec["invoice"]
    header = [f"Invoice No: {inv['invoice_number']}"]
    header += _date_line("Invoice Date", inv["invoice_date"])
    header += _date_line("Delivery Date", inv.get("delivery_date"))
    header += _date_line("Due Date", inv.get("due_date"))
    header += [f"Bill To: {spec['buyer']}", f"From: {spec['vendor']}"]
    return _draw_document(
        out_path,
        "INVOICE",
        header,
        inv["line_items"],
        inv["total_amount"],
        inv.get("adjustments", []),
    )