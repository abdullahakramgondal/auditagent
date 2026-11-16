"""The PDF report of a finished audit: plain words, the same numbers as the screen."""

import io
import json
from datetime import UTC, date, datetime
from decimal import Decimal

import pdfplumber
from fastapi.testclient import TestClient

from auditagent.api.app import create_app
from auditagent.api.jobs import JobManager, JobStore
from auditagent.api.report_pdf import build_report_pdf, pkr
from auditagent.api.schemas import AuditOut, to_audit_out
from auditagent.pipeline.run import AuditReport
from auditagent.rules.engine import audit_invoice
from auditagent.schemas.audit import AuditResult
from auditagent.schemas.contract import ExtractedContract, LatePenaltyRule, Source
from auditagent.schemas.invoice import InvoiceData

PDF = b"%PDF-1.4 test"
CLAUSE = "If delivery is later than 15 October 2026, a penalty of 10% & more shall apply."
TECHNICAL_WORDS = ("Expected", "Billed", "Difference", "Findings")


class SyncExecutor:
    """Runs a job at once, in the calling thread."""

    def submit(self, fn, *args):
        fn(*args)


def make_report(delivered: str = "2026-10-25") -> AuditReport:
    """A report from the real rule engine: 10% of 10,000,000 when the delivery is late."""
    rule = LatePenaltyRule(
        deadline=date(2026, 10, 15),
        mode="flat_percent",
        percent=Decimal(10),
        grace_days=0,
        source=Source(page=4, text=CLAUSE),
    )
    contract = ExtractedContract(rules=[rule])
    invoice = InvoiceData.model_validate(
        {
            "invoice_number": "INV-1",
            "invoice_date": "2026-10-26",
            "delivery_date": delivered,
            "line_items": [
                {
                    "item_name": "Server",
                    "quantity": 10,
                    "unit_price": "1000000",
                    "line_total": "10000000",
                }
            ],
            "total_amount": "10000000",
        }
    )
    result = audit_invoice(contract, invoice)
    return AuditReport(
        result=result, contract=contract, invoice=invoice, purchase_order=None, llm_model="fake-1"
    )


def make_full_report() -> AuditReport:
    """The real tb_09 case: all four kinds of breach (212,500 + 531,250 + 297,500 + a due date)."""
    placeholder = {"page": 6, "text": "The clause text."}
    rules = [
        {
            "clause_type": "late_penalty",
            "deadline": "2027-02-28",
            "mode": "per_day_percent",
            "percent": "2.5",
            "cap_percent": "15",
            "grace_days": 4,
            "source": {
                "page": 4,
                "text": "6.5 If delivery is delayed beyond the Delivery Deadline.",
            },
        },
        {
            "clause_type": "volume_discount",
            "min_quantity": 30,
            "discount_percent": "7",
            "source": {"page": 6, "text": "8.2 A single Order of 30 or more units gets 7%."},
        },
        {
            "clause_type": "unit_price",
            "item_name": "Dell UltraSharp U2723QE Monitor",
            "agreed_unit_price": "85000",
            "source": {"page": 6, "text": "8.1 The agreed unit price is PKR 85,000 per unit."},
        },
        {"clause_type": "payment_terms", "net_days": 28, "source": placeholder},
    ]
    contract = ExtractedContract.model_validate({"rules": rules})
    invoice = InvoiceData.model_validate(
        {
            "invoice_number": "INV-2026-0902",
            "invoice_date": "2027-03-12",
            "delivery_date": "2027-03-09",
            "due_date": "2027-03-30",
            "line_items": [
                {
                    "item_name": "Dell UltraSharp U2723QE Monitor",
                    "quantity": 50,
                    "unit_price": "89250",
                    "line_total": "4462500",
                }
            ],
            "total_amount": "4462500",
        }
    )
    result = audit_invoice(contract, invoice)
    return AuditReport(
        result=result, contract=contract, invoice=invoice, purchase_order=None, llm_model="fake-1"
    )


def text_of(pdf_bytes: bytes) -> str:
    """All the text of a PDF on one line, so that a wrapped sentence can be searched."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return " ".join(" ".join(pages).split())


def out_of(report: AuditReport):
    return to_audit_out("a" * 32, datetime(2026, 11, 15, 11, 28, tzinfo=UTC), report, 12.5)


def test_money_is_written_like_the_screen():
    assert pkr(Decimal("4462500.00")) == "PKR 4,462,500"
    assert pkr(Decimal("1234.5")) == "PKR 1,234.50"
    assert pkr(Decimal(-1736000)) == "-PKR 1,736,000"
    assert pkr(Decimal("0.00")) == "PKR 0"
    assert pkr(None) == "—"


def test_a_too_high_invoice_says_so_in_plain_words_with_the_money_and_the_clause():
    pdf = build_report_pdf(out_of(make_report()))
    assert pdf.startswith(b"%PDF")
    text = text_of(pdf)
    assert "Invoice check report" in text and "This invoice is too high" in text
    assert "Do not pay it as it is." in text
    assert "The vendor is asking for" in text and "The right amount is" in text
    assert "PKR 10,000,000" in text and "PKR 9,000,000" in text and "PKR 1,000,000" in text
    assert "The delivery was late, but no penalty was taken off" in text
    assert "which is 10 days late" in text
    assert "10% of the invoice, once" in text
    assert "What the contract says (page 4)" in text and CLAUSE in text
    assert "Invoice INV-1" in text and "15 Nov 2026, 16:28" in text
    assert "Synthetic or test documents only" in text


def test_the_report_has_no_technical_headings():
    text = text_of(build_report_pdf(out_of(make_report())))
    for word in TECHNICAL_WORDS:
        assert word not in text


def test_the_details_for_a_technician_are_in_the_small_print_at_the_end():
    text = text_of(build_report_pdf(out_of(make_report())))
    assert "Report number " + "a" * 32 in text and "checked by fake-1" in text
    assert text.index("Invoice check report") < text.index("Report number")


def test_a_correct_invoice_says_that_the_buyer_can_pay():
    text = text_of(build_report_pdf(out_of(make_report(delivered="2026-10-14"))))
    assert "This invoice is correct" in text
    assert "You can go ahead and pay it." in text
    assert "Nothing is wrong." in text


def test_every_kind_of_problem_is_explained_with_the_numbers_of_the_contract_and_invoice():
    text = text_of(build_report_pdf(out_of(make_full_report())))
    assert "PKR 1,041,250" in text and "PKR 3,421,250" in text and "PKR 4,462,500" in text
    assert (
        "The contract says each Dell UltraSharp U2723QE Monitor costs PKR 85,000. "
        "The invoice charges PKR 89,250 each for 50 items." in text
    )
    assert "They arrived on 9 March 2027, which is 9 days late." in text
    assert "2.5% of the invoice for each day of delay (the first 4 days are free)" in text
    assert "up to a maximum of 15%" in text
    assert "This order has 50 items, so the discount applies." in text
    assert "which is only 18 days" in text and "until 9 April 2027" in text
    assert "A rule was broken" in text  # the payment terms have no amount
    assert "The contract rules we checked" in text


def test_a_needs_review_report_has_no_amounts_and_asks_for_a_person():
    result = AuditResult(
        status="NEEDS_REVIEW", review_reasons=["invoice: delivery_date: the model returned none"]
    )
    report = AuditReport(result=result, contract=ExtractedContract(rules=[]), llm_model="fake-1")
    text = text_of(build_report_pdf(out_of(report)))
    assert "We could not fully check this invoice" in text
    assert "Please ask a person to look at it before you pay." in text
    assert "Things we could not check" in text
    assert "Delivery date: the model returned none" in text
    assert "The vendor is asking for" not in text


def test_a_long_report_runs_over_to_more_than_one_page():
    report = make_report()
    report.result.findings = report.result.findings * 12
    with pdfplumber.open(io.BytesIO(build_report_pdf(out_of(report)))) as pdf:
        assert len(pdf.pages) > 1


def make_client(tmp_path) -> TestClient:
    manager = JobManager(JobStore(tmp_path / "jobs"), lambda *args: make_report(), SyncExecutor())
    return TestClient(create_app(manager))


def start(client) -> str:
    files = {
        "contract": ("contract.pdf", PDF, "application/pdf"),
        "purchase_order": ("po.pdf", PDF, "application/pdf"),
        "invoice": ("invoice.pdf", PDF, "application/pdf"),
    }
    return client.post("/audits", files=files).json()["audit_id"]


def test_the_report_is_a_downloadable_pdf(tmp_path):
    client = make_client(tmp_path)
    audit_id = start(client)
    response = client.get(f"/audits/{audit_id}/report.pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert f"audit-{audit_id}.pdf" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")
    assert "This invoice is too high" in text_of(response.content)


def test_there_is_no_report_for_an_unknown_audit_or_a_strange_id(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/audits/" + "0" * 32 + "/report.pdf").status_code == 404
    assert client.get("/audits/not-an-id/report.pdf").status_code == 404


def test_the_result_has_a_plain_summary_with_one_problem_for_each_finding():
    plain = out_of(make_full_report()).plain
    assert plain.headline == "This invoice is too high"
    assert plain.advice == "Do not pay it as it is. Ask the vendor for a corrected invoice."
    assert [p.clause_type for p in plain.problems] == [
        "unit_price",
        "late_penalty",
        "volume_discount",
        "payment_terms",
    ]
    assert [p.amount_text for p in plain.problems] == [
        "PKR 212,500 too much",
        "PKR 531,250 too much",
        "PKR 297,500 too much",
        "A rule was broken",
    ]
    assert [p.page for p in plain.problems] == [6, 4, 6, 6]
    price = plain.problems[0]
    assert price.title == "The price per item is higher than agreed"
    assert price.quote == "8.1 The agreed unit price is PKR 85,000 per unit."
    assert price.paragraphs == [
        (
            "The contract says each Dell UltraSharp U2723QE Monitor costs PKR 85,000. "
            "The invoice charges PKR 89,250 each for 50 items."
        )
    ]


def test_a_correct_invoice_has_no_problems_in_its_plain_summary():
    plain = out_of(make_report(delivered="2026-10-14")).plain
    assert plain.headline == "This invoice is correct" and plain.problems == []


def test_a_result_saved_before_the_plain_summary_existed_can_still_be_read():
    old = out_of(make_report()).model_dump_json(exclude={"plain"})
    assert "plain" not in json.loads(old)
    assert AuditOut.model_validate_json(old).plain.headline == "This invoice is too high"


def test_the_result_endpoint_sends_the_plain_summary(tmp_path):
    client = make_client(tmp_path)
    body = client.get(f"/audits/{start(client)}/result").json()
    assert body["plain"]["headline"] == "This invoice is too high"
    problem = body["plain"]["problems"][0]
    assert problem["title"] == "The delivery was late, but no penalty was taken off"
    assert problem["amount_text"] == "PKR 1,000,000 too much" and problem["page"] == 4
