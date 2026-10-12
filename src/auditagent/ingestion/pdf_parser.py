"""Turn a PDF into page-wise text. Pages are numbered by code, not by an LLM."""

import hashlib
import re
import unicodedata
from pathlib import Path

import pdfplumber

from auditagent.schemas.document import PageText, ParsedDocument

MAX_BYTES = 20 * 1024 * 1024
MAX_PAGES = 200

_SPACES = re.compile(r"[ \t]+")


class PdfParseError(Exception):
    """The file cannot be turned into usable page text."""


def clean_text(text: str) -> str:
    """Reading copy: tidy spaces, keep line structure (tables and lists stay readable)."""
    text = unicodedata.normalize("NFKC", text)
    out: list[str] = []
    for line in text.splitlines():
        line = _SPACES.sub(" ", line).strip()
        if line or (out and out[-1]):
            out.append(line)
    return "\n".join(out).strip()


def normalize_for_match(text: str) -> str:
    """Matching copy: one flat line, so a quote can be found even if lines wrapped."""
    return " ".join(unicodedata.normalize("NFKC", text).split())


def parse_pdf(path) -> ParsedDocument:
    path = Path(path)
    if not path.is_file():
        raise PdfParseError(f"File not found: {path.name}")
    size = path.stat().st_size
    if size == 0:
        raise PdfParseError("File is empty")
    if size > MAX_BYTES:
        raise PdfParseError(f"File too large: {size} bytes (limit {MAX_BYTES})")

    data = path.read_bytes()
    if not data.startswith(b"%PDF"):
        raise PdfParseError("Not a PDF file")
    digest = hashlib.sha256(data).hexdigest()

    try:
        with pdfplumber.open(path) as pdf:
            if len(pdf.pages) > MAX_PAGES:
                raise PdfParseError(f"Too many pages: {len(pdf.pages)} (limit {MAX_PAGES})")
            pages = [
                PageText(number=i, text=clean_text(page.extract_text() or ""))
                for i, page in enumerate(pdf.pages, start=1)
            ]
    except PdfParseError:
        raise
    except Exception as exc:  # corrupt, encrypted, unsupported: one clear error for callers
        raise PdfParseError(f"Could not read PDF: {exc}") from exc

    if not pages:
        raise PdfParseError("PDF has no pages")

    warnings = [
        f"Page {p.number} has no extractable text (scanned or image-only?)"
        for p in pages
        if not p.text
    ]
    return ParsedDocument(source_name=path.name, sha256=digest, pages=pages, warnings=warnings)