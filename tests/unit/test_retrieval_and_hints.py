import pytest

from auditagent.agents.legal_extractor import KINDS, RETRIEVAL_QUERIES, hint_fires, retrieve
from auditagent.ingestion.embedder import HashingEmbedder
from auditagent.ingestion.vectorstore import ContractIndex
from auditagent.schemas.chunk import Chunk


def chunks():
    texts = [
        ("1. Delivery", 'The Vendor shall deliver by 31 October 2026 (the "Delivery Deadline").'),
        ("2. Late Delivery", "If the Vendor delivers after the Delivery Deadline, a penalty of 10% applies."),
        ("3. Payment", "Each invoice shall be paid within 30 days of the invoice date."),
        ("4. Pricing", "The unit price of the Server is PKR 1,500,000."),
        ("5. Notices", "Notices must be in writing."),
    ]
    return [
        Chunk(chunk_id=f"x-{i:03d}", page_start=i, page_end=i, heading=h, text=f"{h} {t}")
        for i, (h, t) in enumerate(texts, start=1)
    ]


def test_retrieve_adds_chunks_from_the_extra_query_without_repeats():
    index = ContractIndex(HashingEmbedder(), chunks(), doc_label="t")
    try:
        first = index.search(RETRIEVAL_QUERIES["late_penalty"][0], k=1)[0].chunk
        shown = retrieve(index, "late_penalty", top_k=1, extra_k=2)
    finally:
        index.close()
    ids = [c.chunk_id for c in shown]
    assert ids[0] == first.chunk_id
    assert len(ids) == 3 and len(set(ids)) == 3


def test_a_clause_type_with_one_query_gets_exactly_top_k_chunks():
    index = ContractIndex(HashingEmbedder(), chunks(), doc_label="t")
    try:
        shown = retrieve(index, "unit_price", top_k=3)
    finally:
        index.close()
    assert len(shown) == 3


def test_late_delivery_hint_fires_on_a_delivery_penalty():
    assert hint_fires("late_penalty", "If the Vendor delays delivery, a penalty of 10% shall apply.")


def test_late_payment_charge_is_not_a_late_delivery_hint():
    """Regression (tb_03): a charge on the Buyer for paying late raised a false 'needs review'."""
    assert not hint_fires("late_penalty", "A late payment charge of 2% per month applies if the Buyer pays late.")


def test_payment_hint_needs_an_invoice_and_a_number_of_days():
    assert hint_fires("payment_terms", "All invoices are payable 30 calendar days after the date of invoice.")
    assert hint_fires("payment_terms", "Each invoice shall be paid within thirty (30) days of receipt.")
    assert not hint_fires("payment_terms", "The Buyer shall pay for the goods promptly.")


def test_acknowledging_a_purchase_order_is_not_a_payment_hint():
    """Regression (tb_02): 'within two (2) Business Days' in an order clause raised a false 'needs review'."""
    text = "The Vendor shall acknowledge each Purchase Order in writing within two (2) Business Days of receiving it."
    assert not hint_fires("payment_terms", text)


def test_volume_and_price_hints():
    assert hint_fires("volume_discount", "A discount of 5% applies to orders of 25 or more units.")
    assert not hint_fires("volume_discount", "The Vendor may offer a discount from time to time.")
    assert hint_fires("unit_price", "The unit price of the Server is PKR 1,500,000.")
    assert not hint_fires("unit_price", "The Vendor shall deliver each unit in good condition.")


@pytest.mark.parametrize("kind", KINDS)
def test_text_without_clause_keywords_never_fires(kind):
    assert not hint_fires(kind, "This Agreement is between Buyer Co and Vendor Co.")