import json
from pathlib import Path

from data.generator.commercial_pdf import write_invoice_pdf, write_po_pdf
from data.generator.contract_pdf import read_pages

SPEC = json.loads((Path(__file__).resolve().parents[2] / "data" / "specs" / "case_001.json").read_text())


def test_invoice_pdf_contains_key_fields(tmp_path):
    pdf = write_invoice_pdf(SPEC, tmp_path / "invoice.pdf")
    text = " ".join(read_pages(pdf))
    for piece in ("INV-001", "25 October 2026", "Server", "PKR 10,000,000"):
        assert piece in text


def test_po_pdf_contains_key_fields(tmp_path):
    pdf = write_po_pdf(SPEC, tmp_path / "po.pdf")
    text = " ".join(read_pages(pdf))
    for piece in ("PO-2026-001", "15 October 2026", "Server", "PKR 10,000,000"):
        assert piece in text