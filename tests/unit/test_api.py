"""The HTTP API with a fake runner: no model, no network."""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from auditagent.api.app import create_app
from auditagent.api.auth import UserStore
from auditagent.api.jobs import JobManager, JobStore
from auditagent.ingestion.pdf_parser import PdfParseError
from auditagent.llm.base import LLMError, LLMTransientError
from auditagent.pipeline.run import AuditReport
from auditagent.rules.engine import audit_invoice
from auditagent.schemas.audit import AuditResult
from auditagent.schemas.contract import ExtractedContract, LatePenaltyRule, Source
from auditagent.schemas.invoice import InvoiceData

PDF = b"%PDF-1.4 test"
CLAUSE = "If delivery is later than 15 October 2026, a penalty of 10% shall apply."


class SyncExecutor:
    """Runs a job at once, in the calling thread."""

    def submit(self, fn, *args):
        fn(*args)


class HeldExecutor:
    """Keeps the jobs until the test runs them."""

    def __init__(self):
        self.jobs = []

    def submit(self, fn, *args):
        self.jobs.append(lambda: fn(*args))


def make_report(extra_reasons=()) -> AuditReport:
    """A report from the real rule engine: 10 days late, 10% of 10,000,000."""
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
        }
    )
    result = audit_invoice(contract, invoice, extra_reasons)
    return AuditReport(
        result=result, contract=contract, invoice=invoice, purchase_order=None, llm_model="fake-1"
    )


def runner_returning(report):
    return lambda contract, po, invoice, provider, model: report


def runner_raising(error):
    def runner(contract, po, invoice, provider, model):
        raise error

    return runner


def make_client(tmp_path, runner, executor=None):
    manager = JobManager(JobStore(tmp_path / "jobs"), runner, executor or SyncExecutor())
    client = TestClient(create_app(manager, UserStore(tmp_path / "users.db", rounds=4)))
    reply = client.post(
        "/auth/register", json={"email": "user@example.com", "password": "password123"}
    )
    assert reply.status_code == 200  # the client keeps the login cookie
    return client


def upload(client, contract=PDF, purchase_order=PDF, invoice=PDF, **fields):
    files = {
        "contract": ("contract.pdf", contract, "application/pdf"),
        "purchase_order": ("po.pdf", purchase_order, "application/pdf"),
        "invoice": ("invoice.pdf", invoice, "application/pdf"),
    }
    return client.post("/audits", files=files, data=fields)


def test_health(tmp_path):
    client = make_client(tmp_path, runner_returning(make_report()))
    assert client.get("/health").json() == {"status": "ok"}


def test_an_audit_is_started_and_its_result_has_the_verdict_the_money_and_the_clause(tmp_path):
    client = make_client(tmp_path, runner_returning(make_report()))
    response = upload(client)
    assert response.status_code == 202
    audit_id = response.json()["audit_id"]

    state = client.get(f"/audits/{audit_id}").json()
    assert state["state"] == "done" and state["status"] == "NON_COMPLIANT"

    body = client.get(f"/audits/{audit_id}/result").json()
    assert body["status"] == "NON_COMPLIANT" and body["amounts_provisional"] is False
    assert Decimal(body["billed_total"]) == Decimal(10000000)
    assert Decimal(body["correct_payable"]) == Decimal(9000000)
    assert Decimal(body["total_difference"]) == Decimal(1000000)
    finding = body["findings"][0]
    assert finding["clause_type"] == "late_penalty" and finding["source"]["page"] == 4
    assert finding["source"]["text"] == CLAUSE
    assert body["contract"]["rules"][0]["clause_type"] == "late_penalty"
    assert body["invoice"]["invoice_number"] == "INV-1" and body["llm_model"] == "fake-1"


def test_the_pdfs_and_the_chosen_model_reach_the_runner(tmp_path):
    seen = []

    def runner(contract, po, invoice, provider, model):
        seen.append((provider, model, contract.name, po.name, invoice.name, contract.read_bytes()))
        return make_report()

    client = make_client(tmp_path, runner)
    assert upload(client, provider="ollama", model="qwen2.5:7b").status_code == 202
    assert seen == [("ollama", "qwen2.5:7b", "contract.pdf", "po.pdf", "invoice.pdf", PDF)]


def test_a_file_that_is_not_a_pdf_or_is_empty_is_refused_and_starts_no_job(tmp_path):
    client = make_client(tmp_path, runner_returning(make_report()))
    assert upload(client, contract=b"hello").status_code == 400
    assert upload(client, invoice=b"").status_code == 400
    assert client.get("/audits").json() == []


def test_a_missing_file_is_refused(tmp_path):
    client = make_client(tmp_path, runner_returning(make_report()))
    files = {"contract": ("contract.pdf", PDF, "application/pdf")}
    assert client.post("/audits", files=files).status_code == 422


def test_an_unknown_provider_or_a_strange_model_name_is_refused(tmp_path):
    client = make_client(tmp_path, runner_returning(make_report()))
    assert upload(client, provider="openai").status_code == 400
    assert upload(client, model="a b;c").status_code == 400


def test_a_result_is_not_available_before_the_job_has_run(tmp_path):
    held = HeldExecutor()
    client = make_client(tmp_path, runner_returning(make_report()), held)
    audit_id = upload(client).json()["audit_id"]
    assert client.get(f"/audits/{audit_id}").json()["state"] == "queued"
    assert client.get(f"/audits/{audit_id}/result").status_code == 409
    held.jobs[0]()
    assert client.get(f"/audits/{audit_id}").json()["state"] == "done"
    assert client.get(f"/audits/{audit_id}/result").status_code == 200


def test_a_file_that_cannot_be_parsed_fails_the_job_with_a_clear_reason(tmp_path):
    client = make_client(tmp_path, runner_raising(PdfParseError("Not a PDF file")))
    audit_id = upload(client).json()["audit_id"]
    state = client.get(f"/audits/{audit_id}").json()
    assert state["state"] == "failed" and state["error_kind"] == "bad_file"
    assert "cannot be used" in state["error"]
    assert client.get(f"/audits/{audit_id}/result").status_code == 409


def test_a_busy_model_service_says_to_try_again(tmp_path):
    client = make_client(tmp_path, runner_raising(LLMTransientError("Gemini 503")))
    audit_id = upload(client).json()["audit_id"]
    state = client.get(f"/audits/{audit_id}").json()
    assert state["error_kind"] == "provider_unavailable" and "busy" in state["error"]


def test_a_configuration_error_of_the_model_service_is_shown_and_an_unknown_bug_is_not(tmp_path):
    client = make_client(tmp_path, runner_raising(LLMError("GEMINI_API_KEY is not set.")))
    state = client.get(f"/audits/{upload(client).json()['audit_id']}").json()
    assert state["error_kind"] == "internal" and "GEMINI_API_KEY" in state["error"]

    client = make_client(tmp_path / "other", runner_raising(RuntimeError("secret detail")))
    state = client.get(f"/audits/{upload(client).json()['audit_id']}").json()
    assert state["error_kind"] == "internal" and "secret detail" not in state["error"]


def test_review_reasons_have_a_source_and_a_field_and_the_amounts_are_marked_provisional(tmp_path):
    reasons = ["contract: late_penalty: deadline is not a date", "a plain sentence"]
    client = make_client(tmp_path, runner_returning(make_report(reasons)))
    audit_id = upload(client).json()["audit_id"]
    body = client.get(f"/audits/{audit_id}/result").json()
    assert body["status"] == "NON_COMPLIANT" and body["amounts_provisional"] is True
    assert body["review_reasons"][0] == {
        "source": "contract",
        "field": "late_penalty",
        "reason": "deadline is not a date",
    }
    assert body["review_reasons"][1]["source"] == "audit"


def test_a_needs_review_result_has_no_amounts_and_is_not_provisional(tmp_path):
    result = AuditResult(
        status="NEEDS_REVIEW", review_reasons=["invoice: delivery_date: the model returned none"]
    )
    report = AuditReport(result=result, contract=ExtractedContract(rules=[]), llm_model="fake-1")
    client = make_client(tmp_path, runner_returning(report))
    body = client.get(f"/audits/{upload(client).json()['audit_id']}/result").json()
    assert body["status"] == "NEEDS_REVIEW" and body["billed_total"] is None
    assert body["amounts_provisional"] is False and body["invoice"] is None


def test_the_history_lists_the_newest_audit_first(tmp_path):
    client = make_client(tmp_path, runner_returning(make_report()))
    first = upload(client).json()["audit_id"]
    second = upload(client).json()["audit_id"]
    assert [item["audit_id"] for item in client.get("/audits").json()] == [second, first]


def test_an_unknown_audit_or_a_strange_id_gives_404(tmp_path):
    client = make_client(tmp_path, runner_returning(make_report()))
    for path in ("/audits/" + "0" * 32, "/audits/not-an-id", "/audits/not-an-id/result"):
        assert client.get(path).status_code == 404


def test_the_result_can_be_downloaded_as_a_json_file(tmp_path):
    client = make_client(tmp_path, runner_returning(make_report()))
    audit_id = upload(client).json()["audit_id"]
    response = client.get(f"/audits/{audit_id}/result.json")
    assert response.status_code == 200 and "attachment" in response.headers["content-disposition"]
    assert response.json()["audit_id"] == audit_id
