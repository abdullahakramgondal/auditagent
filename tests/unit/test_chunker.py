from auditagent.ingestion.chunker import chunk_document, strip_page_furniture
from auditagent.schemas.document import PageText, ParsedDocument


def make_doc(pages):
    return ParsedDocument(
        source_name="c.pdf",
        sha256="b" * 64,
        pages=[PageText(number=i, text=t) for i, t in enumerate(pages, start=1)],
    )


def framed(n, total, *lines):
    return "\n".join(["SUPPLY AGREEMENT", *lines, f"Page {n} of {total}"])


DOC = make_doc(
    [
        framed(1, 3, "1. Parties", "This Agreement is between Buyer Co and Vendor Co.",
               "2. Scope of Supply", "The Vendor shall supply the goods in each order."),
        framed(2, 3, "3. Late Delivery",
               "If delivery is later than 15 October 2026, a penalty of 10% shall apply.",
               "4. Warranty", "The Vendor warrants that all goods are new"),
        framed(3, 3, "and free from defects.", "5. Notices", "Notices must be in writing."),
    ]
)


def test_one_chunk_per_clause_with_its_page():
    chunks = chunk_document(DOC)
    assert [c.heading for c in chunks] == [
        "1. Parties", "2. Scope of Supply", "3. Late Delivery", "4. Warranty", "5. Notices"
    ]
    late = chunks[2]
    assert late.page_start == late.page_end == 2
    assert "penalty of 10%" in late.text


def test_repeated_headers_and_footers_are_removed():
    chunks = chunk_document(DOC)
    for c in chunks:
        assert "SUPPLY AGREEMENT" not in c.text
        assert "Page " not in c.text


def test_clause_running_over_a_page_break_is_one_chunk():
    warranty = next(c for c in chunk_document(DOC) if c.heading == "4. Warranty")
    assert (warranty.page_start, warranty.page_end) == (2, 3)
    assert "new and free from defects" in warranty.text


def test_short_documents_keep_all_their_lines():
    doc = make_doc([framed(1, 1, "1. Parties", "Text.")])
    assert strip_page_furniture(doc.pages) == [["SUPPLY AGREEMENT", "1. Parties", "Text.", "Page 1 of 1"]]


def test_long_clause_is_split_with_overlap_and_heading():
    sentences = [f"Sentence number {i} says something useful about delivery." for i in range(40)]
    doc = make_doc(["1. Long Clause\n" + " ".join(sentences)])
    chunks = chunk_document(doc, max_chars=500, overlap=120)
    assert len(chunks) > 2
    assert chunks[0].heading == "1. Long Clause"
    assert all(c.text.startswith("[1. Long Clause]") for c in chunks[1:])
    assert all(len(c.text) < 500 + 120 + 30 for c in chunks)
    # overlap: the last sentence of a piece shows up again at the start of the next one
    last = chunks[0].text.split(". ")[-1].rstrip(".")
    assert last.split(" says")[0] in chunks[1].text


def test_text_without_headings_still_becomes_chunks():
    doc = make_doc(["Just some free text without numbering."])
    chunks = chunk_document(doc)
    assert len(chunks) == 1 and chunks[0].heading == ""


def test_chunking_is_deterministic():
    assert chunk_document(DOC) == chunk_document(DOC)
    ids = [c.chunk_id for c in chunk_document(DOC)]
    assert len(set(ids)) == len(ids)