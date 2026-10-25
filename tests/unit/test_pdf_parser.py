import pytest
from pydantic import ValidationError
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from auditagent.ingestion.pdf_parser import (
    PdfParseError,
    clean_text,
    normalize_for_match,
    parse_pdf,
)
from auditagent.schemas.document import PageText, ParsedDocument
from data.generator.commercial_pdf import write_invoice_pdf

INVOICE_SPEC = {
    "buyer": "Buyer Co",
    "vendor": "Vendor Co",
    "layout": {"doc_variant": 2},
    "invoice": {
        "invoice_number": "INV-001",
        "invoice_date": "2026-10-26",
        "delivery_date": "2026-10-25",
        "line_items": [
            {
                "item_name": "Server",
                "quantity": 10,
                "unit_price": "1000000",
                "line_total": "10000000",
            }
        ],
        "total_amount": "10000000",
    },
}


def make_pdf(path, pages):
    c = canvas.Canvas(str(path), pagesize=A4)
    for text in pages:
        if text:
            c.drawString(72, 700, text)
        c.showPage()
    c.save()
    return path


def test_invoice_pdf_is_parsed_with_page_number_and_hash(tmp_path):
    pdf = write_invoice_pdf(INVOICE_SPEC, tmp_path / "invoice.pdf")
    doc = parse_pdf(pdf)
    assert doc.page_count == 1
    assert "Bill No: INV-001" in doc.page_text(1)
    assert len(doc.sha256) == 64
    assert doc.warnings == []
    assert doc.source_name == "invoice.pdf"


def test_multi_page_numbers_follow_the_pdf(tmp_path):
    pdf = make_pdf(tmp_path / "three.pdf", ["first page", "second page", "third page"])
    doc = parse_pdf(pdf)
    assert [p.number for p in doc.pages] == [1, 2, 3]
    assert "second page" in doc.page_text(2)


def test_blank_page_is_flagged_not_hidden(tmp_path):
    pdf = make_pdf(tmp_path / "blank.pdf", ["has text", ""])
    doc = parse_pdf(pdf)
    assert doc.has_text
    assert len(doc.warnings) == 1 and "Page 2" in doc.warnings[0]


def test_all_blank_document_has_no_text(tmp_path):
    doc = parse_pdf(make_pdf(tmp_path / "scan.pdf", [""]))
    assert not doc.has_text
    assert doc.warnings


def test_bad_files_give_one_clear_error(tmp_path):
    fake = tmp_path / "fake.pdf"
    fake.write_text("this is not a pdf")
    empty = tmp_path / "empty.pdf"
    empty.write_bytes(b"")
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"%PDF-1.4 garbage garbage")
    for bad in (fake, empty, broken, tmp_path / "missing.pdf"):
        with pytest.raises(PdfParseError):
            parse_pdf(bad)


def test_same_file_gives_same_hash_and_different_file_differs(tmp_path):
    a = make_pdf(tmp_path / "a.pdf", ["alpha"])
    b = make_pdf(tmp_path / "b.pdf", ["beta"])
    assert parse_pdf(a).sha256 == parse_pdf(a).sha256
    assert parse_pdf(a).sha256 != parse_pdf(b).sha256


def test_clean_text_keeps_lines_but_tidies_spaces():
    assert clean_text("a   b\t c\n\n\n  d  \n") == "a b c\n\nd"


def test_normalize_for_match_flattens_everything():
    assert normalize_for_match("  15  October\n2026\u00a0 ") == "15 October 2026"


def test_page_numbers_must_be_consecutive():
    sha = "a" * 64
    with pytest.raises(ValidationError):
        ParsedDocument(
            source_name="x.pdf",
            sha256=sha,
            pages=[PageText(number=1, text="a"), PageText(number=3, text="b")],
        )
