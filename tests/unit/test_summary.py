"""The dashboard numbers are counted and added by the backend."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient

from auditagent.api.app import create_app
from auditagent.api.jobs import JobManager, JobStore
from auditagent.api.schemas import JobInfo, summarize


def info(state, status=None, difference=None) -> JobInfo:
    return JobInfo(
        audit_id=uuid4().hex,
        state=state,
        created_at=datetime.now(UTC),
        status=status,
        total_difference=difference,
    )


def make_client(tmp_path) -> tuple[TestClient, JobStore]:
    store = JobStore(tmp_path / "jobs")
    return TestClient(create_app(JobManager(store, lambda *args: None))), store


def test_every_kind_of_audit_is_counted_and_the_money_is_added():
    summary = summarize(
        [
            info("done", "NON_COMPLIANT", Decimal(1000000)),
            info("done", "NON_COMPLIANT", Decimal("41250.50")),
            info("done", "COMPLIANT", Decimal("0.00")),
            info("done", "NEEDS_REVIEW"),
            info("running"),
            info("queued"),
            info("failed"),
        ]
    )
    assert summary.total == 7 and summary.in_progress == 2 and summary.failed == 1
    assert summary.compliant == 1 and summary.non_compliant == 2 and summary.needs_review == 1
    assert summary.total_difference == Decimal("1041250.50")


def test_no_audits_gives_zeros_and_no_money():
    summary = summarize([])
    assert summary.total == 0 and summary.non_compliant == 0
    assert summary.total_difference == Decimal(0)


def test_money_of_a_job_that_is_not_finished_is_not_added():
    assert summarize([info("running", None, Decimal(500))]).total_difference == Decimal(0)


def test_the_summary_address_is_not_taken_for_an_audit_id(tmp_path):
    client, store = make_client(tmp_path)
    response = client.get("/audits/summary")
    assert response.status_code == 200
    assert response.json()["total"] == 0 and Decimal(response.json()["total_difference"]) == 0

    for row in (info("done", "NON_COMPLIANT", Decimal("1041250.00")), info("running")):
        store.create(row.audit_id)
        store.write_info(row)
    body = client.get("/audits/summary").json()
    assert body["total"] == 2 and body["in_progress"] == 1 and body["non_compliant"] == 1
    assert Decimal(body["total_difference"]) == Decimal("1041250.00")
