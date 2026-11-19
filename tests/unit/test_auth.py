"""Accounts, sessions, and the rule that nobody sees the audits of somebody else."""

import sqlite3

from fastapi.testclient import TestClient

from auditagent.api.app import create_app
from auditagent.api.auth import UserStore
from auditagent.api.jobs import JobManager, JobStore
from auditagent.pipeline.run import AuditReport
from auditagent.schemas.audit import AuditResult
from auditagent.schemas.contract import ExtractedContract

PDF = b"%PDF-1.4 test"
PASSWORD = "password123"
REPORT = AuditReport(
    result=AuditResult(status="NEEDS_REVIEW", review_reasons=["invoice: not proven"]),
    contract=ExtractedContract(rules=[]),
    llm_model="fake-1",
)


class SyncExecutor:
    """Runs a job at once, in the calling thread."""

    def submit(self, fn, *args):
        fn(*args)


def make_app(tmp_path):
    manager = JobManager(JobStore(tmp_path / "jobs"), lambda *args: REPORT, SyncExecutor())
    users = UserStore(tmp_path / "users.db", rounds=4)
    return create_app(manager, users), users


def person(app, email):
    """A browser with its own cookies, already registered (and so logged in) as this email."""
    client = TestClient(app)
    reply = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert reply.status_code == 200
    return client


def start(client) -> str:
    files = {
        "contract": ("contract.pdf", PDF, "application/pdf"),
        "purchase_order": ("po.pdf", PDF, "application/pdf"),
        "invoice": ("invoice.pdf", PDF, "application/pdf"),
    }
    reply = client.post("/audits", files=files)
    assert reply.status_code == 202
    return reply.json()["audit_id"]


def test_registering_logs_the_person_in_with_an_http_only_cookie(tmp_path):
    app, _ = make_app(tmp_path)
    client = TestClient(app)
    reply = client.post("/auth/register", json={"email": " Ali@Example.com ", "password": PASSWORD})
    assert reply.status_code == 200 and reply.json() == {"email": "ali@example.com"}
    assert "httponly" in reply.headers["set-cookie"].lower()
    assert client.get("/auth/me").json() == {"email": "ali@example.com"}


def test_a_bad_email_a_short_password_and_a_second_account_with_the_same_email_are_refused(
    tmp_path,
):
    app, _ = make_app(tmp_path)
    client = TestClient(app)
    assert (
        client.post("/auth/register", json={"email": "nope", "password": PASSWORD}).status_code
        == 400
    )
    short = client.post("/auth/register", json={"email": "a@example.com", "password": "short"})
    assert short.status_code == 400 and "at least 8" in short.json()["detail"]
    assert (
        client.post(
            "/auth/register", json={"email": "a@example.com", "password": PASSWORD}
        ).status_code
        == 200
    )
    again = TestClient(app).post(
        "/auth/register", json={"email": "A@example.com", "password": PASSWORD}
    )
    assert again.status_code == 409


def test_the_password_is_stored_hashed(tmp_path):
    app, users = make_app(tmp_path)
    person(app, "a@example.com")
    db = sqlite3.connect(users.path)
    stored = db.execute("SELECT password_hash FROM users").fetchone()[0]
    db.close()
    assert stored.startswith("$2") and PASSWORD not in stored


def test_a_wrong_password_and_an_unknown_email_get_the_same_answer(tmp_path):
    app, _ = make_app(tmp_path)
    person(app, "a@example.com")
    wrong = TestClient(app).post(
        "/auth/login", json={"email": "a@example.com", "password": "bad-password"}
    )
    unknown = TestClient(app).post(
        "/auth/login", json={"email": "b@example.com", "password": PASSWORD}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": "Wrong email or password."}


def test_logging_out_ends_the_session(tmp_path):
    app, _ = make_app(tmp_path)
    client = person(app, "a@example.com")
    assert client.get("/auth/me").status_code == 200
    assert client.post("/auth/logout").json() == {"status": "ok"}
    assert client.get("/auth/me").status_code == 401


def test_an_expired_session_does_not_work(tmp_path):
    app, users = make_app(tmp_path)
    client = person(app, "a@example.com")
    db = sqlite3.connect(users.path)
    db.execute("UPDATE sessions SET expires_at = '2000-01-01T00:00:00+00:00'")
    db.commit()
    db.close()
    assert client.get("/auth/me").status_code == 401


def test_without_a_login_every_audit_address_says_please_log_in(tmp_path):
    app, _ = make_app(tmp_path)
    client = TestClient(app)
    for path in (
        "/audits",
        "/audits/summary",
        "/audits/" + "0" * 32,
        "/audits/" + "0" * 32 + "/result",
    ):
        reply = client.get(path)
        assert reply.status_code == 401 and reply.json() == {"detail": "Please log in."}
    files = {"contract": ("c.pdf", PDF, "application/pdf")}
    assert client.post("/audits", files=files).status_code == 401
    assert client.get("/health").status_code == 200  # the health check stays public


def test_a_person_sees_all_of_their_own_audits_and_nobody_elses(tmp_path):
    app, _ = make_app(tmp_path)
    ali = person(app, "ali@example.com")
    sara = person(app, "sara@example.com")
    ali_ids = [start(ali) for _ in range(3)]
    sara_id = start(sara)

    assert sorted(item["audit_id"] for item in ali.get("/audits").json()) == sorted(ali_ids)
    assert [item["audit_id"] for item in sara.get("/audits").json()] == [sara_id]
    assert ali.get("/audits/summary").json()["total"] == 3
    assert sara.get("/audits/summary").json()["total"] == 1


def test_nobody_can_open_the_audit_of_somebody_else_by_its_id(tmp_path):
    app, _ = make_app(tmp_path)
    ali = person(app, "ali@example.com")
    sara = person(app, "sara@example.com")
    audit_id = start(ali)
    assert ali.get(f"/audits/{audit_id}/result").status_code == 200

    for path in (
        f"/audits/{audit_id}",
        f"/audits/{audit_id}/result",
        f"/audits/{audit_id}/result.json",
        f"/audits/{audit_id}/report.pdf",
    ):
        reply = sara.get(path)
        assert reply.status_code == 404, path  # the same answer as for an audit that does not exist
        assert reply.json() == {"detail": "Unknown audit."} or path.endswith(".pdf")


def test_the_history_is_still_there_after_logging_out_and_in_again(tmp_path):
    app, _ = make_app(tmp_path)
    ali = person(app, "ali@example.com")
    ids = [start(ali) for _ in range(3)]
    ali.post("/auth/logout")
    assert ali.get("/audits").status_code == 401

    back = ali.post("/auth/login", json={"email": "ali@example.com", "password": PASSWORD})
    assert back.status_code == 200
    assert sorted(item["audit_id"] for item in ali.get("/audits").json()) == sorted(ids)


def test_an_audit_without_an_owner_belongs_to_nobody(tmp_path):
    app, _ = make_app(tmp_path)
    manager_store = JobStore(tmp_path / "jobs")
    ali = person(app, "ali@example.com")
    audit_id = start(ali)
    info = manager_store.read_info(audit_id)
    info.user_id = None  # like an audit made before accounts existed
    manager_store.write_info(info)
    assert ali.get("/audits").json() == []
    assert ali.get(f"/audits/{audit_id}").status_code == 404
