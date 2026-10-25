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


def test_the_late_word_may_come_after_the_percentage():
    """Regression (tb_01): the only 'delay' sits after the 8%, so the hint stayed silent on an empty answer."""
    text = (
        "6.4 Time is of the essence for delivery. Should the Vendor deliver any Equipment after 20 November 2026, "
        "it shall pay to the Buyer a penalty equal to 8% of the invoice value of the Equipment so delivered. "
        "The Parties agree that no penalty shall accrue in respect of the first five (5) days of delay following "
        "that date."
    )
    assert hint_fires("late_penalty", text)


def test_the_late_word_may_come_after_the_percentage_in_a_long_clause():
    """Regression (tb_04): 'late delivery' is written after the 10% and after a long sentence."""
    text = (
        "Where the Vendor delivers the Equipment after the Delivery Deadline, the Vendor shall pay to the Buyer "
        "a sum equal to 10% of the invoice value of the Equipment so delivered. This amount is payable once only "
        "in respect of the late delivery, and does not increase with the length of the delay."
    )
    assert hint_fires("late_penalty", text)


def test_late_payment_charge_is_not_a_late_delivery_hint():
    """Regression (tb_03): a charge on the Buyer for paying late raised a false 'needs review'."""
    assert not hint_fires("late_penalty", "A late payment charge of 2% per month applies if the Buyer pays late.")


@pytest.mark.parametrize(
    "text",
    [
        "If the Buyer delays payment beyond the due date, a late payment charge of 2% applies.",
        "Where there is a delay in payment, interest of 2% per month is charged.",
        "5. Late Payment Charge If the Buyer delays the payment of an invoice, 2% is added.",
    ],
)
def test_delayed_payment_is_not_a_late_delivery_hint(text):
    """Regression (gen_018, 022, 023, 024): 'delays payment ... 2%' raised a false 'needs review'."""
    assert not hint_fires("late_penalty", text)


def test_payment_hint_needs_an_invoice_a_payment_word_and_a_number_of_days():
    assert hint_fires("payment_terms", "All invoices are payable 30 calendar days after the date of invoice.")
    assert hint_fires("payment_terms", "Each invoice shall be paid within thirty (30) days of receipt.")
    assert not hint_fires("payment_terms", "The Buyer shall pay for the goods promptly.")


def test_acknowledging_a_purchase_order_is_not_a_payment_hint():
    """Regression (tb_02): 'within two (2) Business Days' in an order clause raised a false 'needs review'."""
    text = "The Vendor shall acknowledge each Purchase Order in writing within two (2) Business Days of receiving it."
    assert not hint_fires("payment_terms", text)


def test_a_delivery_penalty_that_mentions_the_invoice_and_days_is_not_a_payment_hint():
    """Regression (gen_007): 'final invoice' and 'not more than 3 days' in a penalty clause raised a false alarm."""
    text = (
        "10. Delivery and Late Delivery If delivery of the goods is later than 9 October 2026, a penalty of 15% "
        "shall apply to the final invoice. No penalty applies if the delay is not more than 3 days."
    )
    assert not hint_fires("payment_terms", text)
    assert hint_fires("late_penalty", text)  # it is still a delivery penalty


def test_volume_and_price_hints():
    assert hint_fires("volume_discount", "A discount of 5% applies to orders of 25 or more units.")
    assert not hint_fires("volume_discount", "The Vendor may offer a discount from time to time.")
    assert hint_fires("unit_price", "The unit price of the Server is PKR 1,500,000.")
    assert not hint_fires("unit_price", "The Vendor shall deliver each unit in good condition.")


def test_the_price_may_come_before_the_word_unit():
    """Regression (gen_011): 'PKR 1,150,000 per unit' has the price first, so the hint stayed silent."""
    text = "The Vendor shall supply Leased Line 100 Mbps (annual) at a fixed rate of PKR 1,150,000 per unit."
    assert hint_fires("unit_price", text)


def test_a_volume_reduction_is_a_volume_discount_hint():
    """Regression (tb_08): 'a volume reduction of 2%' was not a hint, so an empty model answer stayed silent."""
    text = (
        "8.2 Where a single Order contains ten (10) or more units, a volume reduction of 2% shall be applied "
        "to the Equipment value for that Order."
    )
    assert hint_fires("volume_discount", text)


def test_the_percentage_may_come_before_the_discount_word():
    assert hint_fires("volume_discount", "A 5% volume discount applies to orders of 25 or more units.")


def test_a_late_payment_charge_is_not_a_volume_discount_hint():
    """tb_08 clause 9.3 sits next to the volume clause and must not fire."""
    text = "The Vendor may charge a late payment charge of 2% per month on an amount that remains overdue and undisputed."
    assert not hint_fires("volume_discount", text)


@pytest.mark.parametrize("kind", KINDS)
def test_text_without_clause_keywords_never_fires(kind):
    assert not hint_fires(kind, "This Agreement is between Buyer Co and Vendor Co.")