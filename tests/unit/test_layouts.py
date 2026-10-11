import json

import pytest

from data.generator.commercial_pdf import (
    DOC_VARIANTS,
    LABELS,
    fmt_doc_date,
    write_invoice_pdf,
    write_po_pdf,
)
from data.generator.contract_pdf import read_pages

LINES = [
    {"item_name": "Fortinet FortiGate 100F Firewall", "quantity": 10,
     "unit_price": "1000000", "line_total": "10000000"},
    {"item_name": "APC Smart-UPS 3000VA", "quantity": 4,
     "unit_price": "250000", "line_total": "1000000"},
]

SPEC = {
    "buyer": "Five Rivers Technologies Pvt Ltd",
    "vendor": "Leased Vendor Pvt Ltd",
    "layout": {},
    "purchase_order": {
        "po_number": "PO-2026-001",
        "po_date": "2026-09-01",
        "delivery_due_date": "2026-10-15",
        "line_items": LINES,
        "total_amount": "11000000",
    },
    "invoice": {
        "invoice_number": "INV-001",
        "invoice_date": "2026-10-26",
        "delivery_date": "2026-10-25",
        "due_date": "2026-11-25",
        "line_items": LINES,
        "adjustments": [{"label": "Less: volume discount", "amount": "-550000"}],
        "total_amount": "10450000",
    },
}


def spec_for(variant):
    spec = json.loads(json.dumps(SPEC))
    spec["layout"]["doc_variant"] = variant
    return spec


def read(pdf):
    return " ".join(read_pages(pdf))


@pytest.mark.parametrize("variant", DOC_VARIANTS)
def test_invoice_fields_survive_every_layout(variant, tmp_path):
    spec = spec_for(variant)
    text = read(write_invoice_pdf(spec, tmp_path / "invoice.pdf"))
    lab = LABELS["invoice"][variant]
    inv = spec["invoice"]
    assert f"{lab['number']}: INV-001" in text
    assert f"{lab['delivery']}: {fmt_doc_date(inv['delivery_date'], variant)}" in text
    assert f"{lab['due']}: {fmt_doc_date(inv['due_date'], variant)}" in text
    assert "Fortinet FortiGate 100F Firewall" in text
    assert "Less: volume discount" in text and "550,000" in text
    assert "PKR 10,450,000" in text
    assert spec["buyer"] in text and spec["vendor"] in text


@pytest.mark.parametrize("variant", DOC_VARIANTS)
def test_po_fields_survive_every_layout(variant, tmp_path):
    spec = spec_for(variant)
    text = read(write_po_pdf(spec, tmp_path / "po.pdf"))
    lab = LABELS["po"][variant]
    po = spec["purchase_order"]
    assert f"{lab['number']}: PO-2026-001" in text
    assert f"{lab['due']}: {fmt_doc_date(po['delivery_due_date'], variant)}" in text
    assert "APC Smart-UPS 3000VA" in text
    assert "PKR 11,000,000" in text


def test_layouts_really_differ(tmp_path):
    texts = {v: read(write_invoice_pdf(spec_for(v), tmp_path / f"i{v}.pdf")) for v in DOC_VARIANTS}
    assert len(set(texts.values())) == 3


def test_unknown_variant_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        write_invoice_pdf(spec_for(9), tmp_path / "x.pdf")


def test_default_layout_is_variant_one(tmp_path):
    spec = json.loads(json.dumps(SPEC))
    text = read(write_invoice_pdf(spec, tmp_path / "x.pdf"))
    assert "Invoice No: INV-001" in text and "25 October 2026" in text