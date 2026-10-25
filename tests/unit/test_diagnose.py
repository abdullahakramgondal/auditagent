from auditagent.ingestion.embedder import HashingEmbedder
from auditagent.schemas.document import PageText, ParsedDocument
from eval.diagnose import retrieval_report

PAGES = [
    (
        "SUPPLY AGREEMENT\n1. Parties\nThis Agreement is between Buyer Co and Vendor Co.\n"
        "2. Scope of Supply\nThe Vendor shall supply the goods.\nPage 1 of 3"
    ),
    (
        "SUPPLY AGREEMENT\n3. Price\nThe price payable for each Unit of the Lenovo ThinkPad T14 Laptop shall be PKR 275,000 "
        "and the agreed unit price shall not be exceeded.\n4. Warranty\nThe Vendor warrants that all goods are new.\nPage 2 of 3"
    ),
    "SUPPLY AGREEMENT\n5. Payment\nEach invoice shall be paid within 60 days.\n6. Notices\nNotices must be in writing.\nPage 3 of 3",
]


def doc():
    return ParsedDocument(
        source_name="c.pdf",
        sha256="c" * 64,
        pages=[PageText(number=i, text=t) for i, t in enumerate(PAGES, start=1)],
    )


def test_chunk_holding_the_needle_is_ranked_and_sent_to_the_model():
    report = retrieval_report(doc(), "unit_price", "275,000", HashingEmbedder(), top_k=5)
    assert report["chunk_count"] == 6
    assert len(report["top"]) == 5 and len(report["prompt_chunks"]) == 5
    assert report["needle_ranks"] == [1]
    _rank, chunk, found = report["top"][0]
    assert found and chunk.heading.startswith("3. Price") and chunk.page_start == 2


def test_a_needle_that_is_not_in_the_contract_gives_no_ranks():
    report = retrieval_report(doc(), "unit_price", "999,999", HashingEmbedder())
    assert report["needle_ranks"] == []
