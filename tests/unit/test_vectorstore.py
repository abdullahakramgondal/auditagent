import math

import pytest

from auditagent.ingestion.embedder import HashingEmbedder
from auditagent.ingestion.vectorstore import ContractIndex
from auditagent.schemas.chunk import Chunk


def chunks():
    texts = [
        ("1. Late Delivery", "If delivery is later than 15 October 2026, a penalty of 10% shall apply to the final invoice."),
        ("2. Payment Terms", "All invoices are payable 30 calendar days after the date of invoice."),
        ("3. Limitation of Liability", "The total liability of either party shall not exceed 10% of the total order value."),
        ("4. Confidentiality", "Each party shall keep the terms of this Agreement confidential."),
    ]
    return [
        Chunk(chunk_id=f"x-{i:03d}", page_start=i, page_end=i, heading=h, text=f"{h} {t}")
        for i, (h, t) in enumerate(texts, start=1)
    ]


def test_hashing_embedder_is_deterministic_and_unit_length():
    emb = HashingEmbedder()
    a1, a2, b = emb.embed(["late delivery penalty", "late delivery penalty", "payment terms"])
    assert a1 == a2 and a1 != b
    assert math.isclose(sum(v * v for v in a1), 1.0, rel_tol=1e-9)


def test_search_finds_the_penalty_clause_first():
    index = ContractIndex(HashingEmbedder(), chunks(), doc_label="t")
    hits = index.search("penalty for late delivery shall apply to the final invoice", k=3)
    assert hits[0].chunk.heading == "1. Late Delivery"
    assert hits[0].chunk.page_start == 1
    assert len(hits) == 3
    assert hits[0].distance <= hits[1].distance <= hits[2].distance
    index.close()


def test_k_is_clamped_to_the_number_of_chunks():
    index = ContractIndex(HashingEmbedder(), chunks(), doc_label="t")
    assert len(index.search("anything", k=50)) == 4
    index.close()


def test_two_indexes_do_not_see_each_other():
    first = ContractIndex(HashingEmbedder(), chunks(), doc_label="t")
    second = ContractIndex(HashingEmbedder(), chunks()[:1], doc_label="t")
    assert len(first.search("late", k=10)) == 4
    assert len(second.search("late", k=10)) == 1
    first.close()
    second.close()


def test_indexing_nothing_is_an_error():
    with pytest.raises(ValueError):
        ContractIndex(HashingEmbedder(), [], doc_label="t")