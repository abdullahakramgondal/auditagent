"""Render a contract spec into a multi-page PDF and read it back."""

from pathlib import Path

import pdfplumber
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

from data.generator.templates import build_contract_sections, render_clause

PAGE_W, PAGE_H = A4
MARGIN = 56
FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
SIZE = 11
LEADING = 15
MIN_BLOCKS_PER_PAGE = 3

# Generic padding text. No numbers or percentages on purpose.
BOILERPLATE = [
    (
        "General Provisions",
        "This Agreement is the entire understanding between the parties and replaces all earlier discussions.",
    ),
    (
        "Notices",
        "Any notice under this Agreement must be in writing and sent to the registered address of the other party.",
    ),
    (
        "Governing Law",
        "This Agreement is governed by the laws of Pakistan and disputes shall be heard by the courts of Lahore.",
    ),
    (
        "Assignment",
        "Neither party may assign its rights under this Agreement without the written consent of the other.",
    ),
    (
        "Amendments",
        "Changes to this Agreement are valid only if made in writing and signed by both parties.",
    ),
    (
        "Severability",
        "If any provision is held invalid, the remaining provisions continue in full effect.",
    ),
]


def _assign_pages(sections, total_pages, target_pages):
    pages = [[] for _ in range(total_pages)]
    rest = []
    for s in sections:
        if s["key"] in ("parties", "scope"):
            pages[0].append(s)
        elif s["key"] in target_pages:
            idx = min(max(target_pages[s["key"]], 1), total_pages) - 1
            pages[idx].append(s)
        else:
            rest.append(s)
    for i, s in enumerate(rest):
        idx = 1 + (i % (total_pages - 1)) if total_pages > 1 else 0
        pages[idx].append(s)
    n = 0
    for page in pages:
        while len(page) < MIN_BLOCKS_PER_PAGE:
            title, text = BOILERPLATE[n % len(BOILERPLATE)]
            page.append({"key": "boilerplate", "title": title, "text": text})
            n += 1
    return pages


def write_contract_pdf(spec: dict, out_path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    sections = build_contract_sections(spec)
    total = spec["layout"]["contract_pages"]
    pages = _assign_pages(sections, total, spec["layout"].get("target_page", {}))

    c = canvas.Canvas(str(out_path), pagesize=A4)
    width = PAGE_W - 2 * MARGIN
    number = 1
    for page_no, blocks in enumerate(pages, start=1):
        y = PAGE_H - MARGIN
        c.setFont(FONT_BOLD, 14)
        c.drawString(MARGIN, y, "SUPPLY AGREEMENT")
        y -= 36
        for block in blocks:
            c.setFont(FONT_BOLD, SIZE)
            c.drawString(MARGIN, y, f"{number}. {block['title']}")
            number += 1
            y -= LEADING + 2
            c.setFont(FONT, SIZE)
            for line in simpleSplit(block["text"], FONT, SIZE, width):
                c.drawString(MARGIN, y, line)
                y -= LEADING
            y -= 12
        if y < MARGIN:
            raise ValueError(f"Page {page_no} overflows; use more pages or fewer clauses")
        c.setFont(FONT, 9)
        c.drawString(MARGIN, MARGIN / 2, f"Page {page_no} of {total}")
        c.showPage()
    c.save()
    return out_path


def _norm(text: str) -> str:
    return " ".join(text.split())


def read_pages(pdf_path) -> list[str]:
    with pdfplumber.open(pdf_path) as pdf:
        return [_norm(p.extract_text() or "") for p in pdf.pages]


def locate_rules(spec: dict, pdf_path) -> dict:
    """Find the page where each rule's clause text really appears in the PDF."""
    pages = read_pages(pdf_path)
    variant = spec["layout"]["wording_variant"]
    found = {}
    for rule in spec["rules"]:
        text = render_clause(rule, variant)
        needle = _norm(text)
        hits = [i + 1 for i, p in enumerate(pages) if needle in p]
        found[rule["clause_type"]] = {"page": hits[0] if hits else None, "text": text}
    return found
