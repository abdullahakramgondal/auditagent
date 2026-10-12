"""Split a parsed contract into clause-sized chunks that remember their page."""

import re

from auditagent.schemas.chunk import Chunk
from auditagent.schemas.document import PageText, ParsedDocument

MAX_CHARS = 1200
OVERLAP_CHARS = 150
FURNITURE_ZONE = 2  # look at the first and last N lines of each page
FURNITURE_MAX_CHARS = 60
FURNITURE_RATIO = 0.6

_HEADING = re.compile(r"^(?:\d+\.\s+|\d+\.\d+(?:\.\d+)*\.?\s+)[A-Z]")
_SENTENCE_END = re.compile(r"(?<=[.;])\s+")
_DIGITS = re.compile(r"\d+")


def _line_key(line: str) -> str:
    return _DIGITS.sub("#", line.strip())


def strip_page_furniture(pages: list[PageText]) -> list[list[str]]:
    """Lines per page, without headers and footers that repeat on most pages."""
    per_page = [[ln for ln in p.text.splitlines() if ln.strip()] for p in pages]
    if len(pages) < 3:
        return per_page

    def zone(lines):
        n = len(lines)
        return set(range(min(FURNITURE_ZONE, n))) | set(range(max(0, n - FURNITURE_ZONE), n))

    counts: dict[str, int] = {}
    for lines in per_page:
        keys = {_line_key(lines[i]) for i in zone(lines) if len(lines[i]) <= FURNITURE_MAX_CHARS}
        for key in keys:
            counts[key] = counts.get(key, 0) + 1
    furniture = {k for k, c in counts.items() if c / len(pages) >= FURNITURE_RATIO}

    cleaned = []
    for lines in per_page:
        z = zone(lines)
        cleaned.append(
            [
                ln
                for i, ln in enumerate(lines)
                if not (i in z and len(ln) <= FURNITURE_MAX_CHARS and _line_key(ln) in furniture)
            ]
        )
    return cleaned


def _blocks(per_page: list[list[str]]) -> list[dict]:
    blocks: list[dict] = []
    current = None
    for page_no, lines in enumerate(per_page, start=1):
        for line in lines:
            is_heading = bool(_HEADING.match(line))
            if is_heading or current is None:
                if current:
                    blocks.append(current)
                current = {"start": page_no, "end": page_no, "lines": [line], "titled": is_heading}
            else:
                current["lines"].append(line)
                current["end"] = page_no
    if current:
        blocks.append(current)
    return blocks


def _split_long(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    sentences: list[str] = []
    for s in _SENTENCE_END.split(text):
        while len(s) > max_chars:
            sentences.append(s[:max_chars])
            s = s[max_chars:]
        if s:
            sentences.append(s)

    pieces: list[str] = []
    current: list[str] = []
    size = 0
    for s in sentences:
        if current and size + len(s) + 1 > max_chars:
            pieces.append(" ".join(current))
            keep: list[str] = []
            kept = 0
            for prev in reversed(current):
                if kept + len(prev) > overlap:
                    break
                keep.insert(0, prev)
                kept += len(prev) + 1
            current, size = keep, kept
        current.append(s)
        size += len(s) + 1
    if current:
        pieces.append(" ".join(current))
    return pieces


def chunk_document(
    doc: ParsedDocument, max_chars: int = MAX_CHARS, overlap: int = OVERLAP_CHARS
) -> list[Chunk]:
    """One chunk per numbered clause (long clauses are split with overlap)."""
    chunks: list[Chunk] = []
    for block in _blocks(strip_page_furniture(doc.pages)):
        heading = block["lines"][0][:80] if block["titled"] else ""
        text = " ".join(block["lines"])
        for i, piece in enumerate(_split_long(text, max_chars, overlap)):
            if i > 0 and heading:
                piece = f"[{heading}] {piece}"
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.sha256[:12]}-{len(chunks) + 1:03d}",
                    page_start=block["start"],
                    page_end=block["end"],
                    heading=heading,
                    text=piece,
                )
            )
    return chunks