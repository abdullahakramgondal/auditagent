"""The production server: the API under /api, the built front end at /, client routes open the app."""

import pytest
from fastapi.testclient import TestClient

from auditagent.api.auth import UserStore
from auditagent.api.jobs import JobManager, JobStore
from auditagent.api.web import create_web_app

INDEX = "<!doctype html><title>AuditAgent test page</title>"


def make_client(tmp_path) -> TestClient:
    """A web app over a tiny fake build: index.html and one file under assets."""
    web = tmp_path / "dist"
    (web / "assets").mkdir(parents=True)
    (web / "index.html").write_text(INDEX)
    (web / "assets" / "app.js").write_text("console.log(1)")
    manager = JobManager(JobStore(tmp_path / "jobs"), lambda *args: None)
    users = UserStore(tmp_path / "users.db", rounds=4)
    return TestClient(create_web_app(manager, web, users))


def log_in(client: TestClient) -> None:
    body = {"email": "a@example.com", "password": "password123"}
    assert client.post("/api/auth/register", json=body).status_code == 200


def test_the_root_opens_the_front_end(tmp_path):
    response = make_client(tmp_path).get("/")
    assert response.status_code == 200 and "AuditAgent test page" in response.text


def test_a_route_of_the_front_end_opens_the_app_after_a_reload(tmp_path):
    client = make_client(tmp_path)
    for path in ("/login", "/history", "/audits/3f9c2a7e5b1d4c8a9e0f6b2d7a1c4e83"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert "text/html" in response.headers["content-type"], path
        assert "AuditAgent test page" in response.text, path


def test_the_api_answers_under_api_and_needs_a_login_for_audits(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/audits").status_code == 401
    log_in(client)  # the cookie works under /api
    assert client.get("/api/audits").json() == []


def test_an_unknown_api_address_is_a_json_404_and_not_the_app(tmp_path):
    client = make_client(tmp_path)
    log_in(client)
    response = client.get("/api/audits/not-an-id")
    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown audit."}


def test_a_built_file_is_served_and_a_missing_one_is_a_404(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/assets/app.js").text == "console.log(1)"
    assert client.get("/assets/missing.js").status_code == 404


def test_a_missing_build_says_how_to_make_it(tmp_path):
    with pytest.raises(RuntimeError, match="npm run build"):
        create_web_app(web_dir=tmp_path / "nothing")
