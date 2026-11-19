"""The HTTP API: accounts, upload three PDFs, poll the job, read the result.

Every audit belongs to the person who started it. Asking for the audit of somebody else gives
404 (the same as an audit that does not exist), so nobody can even learn that it exists.

Run (project root):  uvicorn auditagent.api.app:create_app --factory --reload
Interactive docs:    http://127.0.0.1:8000/docs
Environment: AUDITAGENT_JOBS_DIR (default data/jobs), AUDITAGENT_DB (default data/auditagent.db),
AUDITAGENT_CORS_ORIGINS (comma separated), AUDITAGENT_COOKIE_SECURE=1 once the site uses HTTPS.
Synthetic or test documents only: the text of the documents goes to the chosen model.
"""

import os
import re
from pathlib import Path
from typing import Annotated

from fastapi import Cookie, Depends, FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from auditagent.api.auth import (
    COOKIE,
    SESSION_DAYS,
    AuthError,
    Credentials,
    User,
    UserOut,
    UserStore,
)
from auditagent.api.jobs import JobManager, JobStore
from auditagent.api.report_pdf import build_report_pdf
from auditagent.api.runner import run_audit
from auditagent.api.schemas import AuditOut, AuditSummary, JobInfo, Submitted, summarize

MAX_BYTES = 10 * 1024 * 1024
PROVIDERS = ("gemini", "ollama")
_MODEL_NAME = re.compile(r"^[A-Za-z0-9._:/-]{1,60}$")


def default_manager() -> JobManager:
    root = Path(os.environ.get("AUDITAGENT_JOBS_DIR", "data/jobs"))
    return JobManager(JobStore(root), run_audit)


def default_users() -> UserStore:
    return UserStore(Path(os.environ.get("AUDITAGENT_DB", "data/auditagent.db")))


async def read_pdf(upload: UploadFile, label: str) -> bytes:
    """The bytes of an uploaded file, refused early when it cannot be a usable PDF."""
    data = await upload.read(MAX_BYTES + 1)
    if not data:
        raise HTTPException(400, f"The {label} file is empty.")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, f"The {label} file is larger than {MAX_BYTES // 2**20} MB.")
    if not data.startswith(b"%PDF"):
        raise HTTPException(400, f"The {label} file is not a PDF.")
    return data


def create_app(manager: JobManager | None = None, users: UserStore | None = None) -> FastAPI:
    """The application. Tests pass a manager with a fake runner and a user store in a temp folder."""
    jobs = manager or default_manager()
    accounts = users or default_users()
    secure_cookie = os.environ.get("AUDITAGENT_COOKIE_SECURE") == "1"
    app = FastAPI(title="AuditAgent AI", version="0.2.0")
    origins = os.environ.get("AUDITAGENT_CORS_ORIGINS", "http://localhost:5173")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in origins.split(",") if origin.strip()],
        allow_credentials=True,  # the browser sends the login cookie
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def current_user(session: Annotated[str | None, Cookie(alias=COOKIE)] = None) -> User:
        user = accounts.user_for_token(session) if session else None
        if user is None:
            raise HTTPException(401, "Please log in.")
        return user

    def owned(audit_id: str, user: User) -> JobInfo:
        """The job of this audit, only if it belongs to this person (else 404, like an unknown one)."""
        info = jobs.store.read_info(audit_id)
        if info is None or info.user_id != user.id:
            raise HTTPException(404, "Unknown audit.")
        return info

    def mine(user: User) -> list[JobInfo]:
        return [info for info in jobs.store.list_infos() if info.user_id == user.id]

    def start_session(response: Response, user: User) -> UserOut:
        token = accounts.new_session(user.id)
        response.set_cookie(
            COOKIE,
            token,
            max_age=SESSION_DAYS * 24 * 3600,
            httponly=True,
            samesite="lax",
            secure=secure_cookie,
            path="/",
        )
        return UserOut(email=user.email)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    # ---- accounts ----

    @app.post("/auth/register", response_model=UserOut)
    def register(body: Credentials, response: Response) -> UserOut:
        try:
            user = accounts.create_user(body.email, body.password)
        except AuthError as exc:
            raise HTTPException(exc.status, exc.message) from exc
        return start_session(response, user)

    @app.post("/auth/login", response_model=UserOut)
    def login(body: Credentials, response: Response) -> UserOut:
        try:
            user = accounts.login(body.email, body.password)
        except AuthError as exc:
            raise HTTPException(exc.status, exc.message) from exc
        return start_session(response, user)

    @app.post("/auth/logout")
    def logout(
        response: Response, session: Annotated[str | None, Cookie(alias=COOKIE)] = None
    ) -> dict:
        if session:
            accounts.end_session(session)
        response.delete_cookie(COOKIE, path="/")
        return {"status": "ok"}

    @app.get("/auth/me", response_model=UserOut)
    def me(user: Annotated[User, Depends(current_user)]) -> UserOut:
        return UserOut(email=user.email)

    # ---- audits (every one of them belongs to a person) ----

    @app.post("/audits", status_code=202, response_model=Submitted)
    async def start_audit(
        contract: Annotated[UploadFile, File()],
        purchase_order: Annotated[UploadFile, File()],
        invoice: Annotated[UploadFile, File()],
        user: Annotated[User, Depends(current_user)],
        provider: Annotated[str | None, Form()] = None,
        model: Annotated[str | None, Form()] = None,
    ) -> Submitted:
        if provider and provider not in PROVIDERS:
            raise HTTPException(400, f"The provider must be one of: {', '.join(PROVIDERS)}.")
        if model and not _MODEL_NAME.match(model):
            raise HTTPException(400, "The model name has characters that are not allowed.")
        pdfs = {
            "contract": await read_pdf(contract, "contract"),
            "purchase_order": await read_pdf(purchase_order, "purchase order"),
            "invoice": await read_pdf(invoice, "invoice"),
        }
        info = jobs.submit(pdfs, provider or None, model or None, user.id)
        return Submitted(audit_id=info.audit_id)

    @app.get("/audits", response_model=list[JobInfo])
    def history(user: Annotated[User, Depends(current_user)]) -> list[JobInfo]:
        return mine(user)

    @app.get("/audits/summary", response_model=AuditSummary)
    def summary(user: Annotated[User, Depends(current_user)]) -> AuditSummary:
        return summarize(mine(user))

    @app.get("/audits/{audit_id}", response_model=JobInfo)
    def job_state(audit_id: str, user: Annotated[User, Depends(current_user)]) -> JobInfo:
        return owned(audit_id, user)

    @app.get("/audits/{audit_id}/result", response_model=AuditOut)
    def result(audit_id: str, user: Annotated[User, Depends(current_user)]) -> AuditOut:
        info = owned(audit_id, user)
        if info.state != "done":
            raise HTTPException(409, info.error or f"The audit is {info.state}.")
        out = jobs.store.read_result(audit_id)
        if out is None:
            raise HTTPException(500, "The result file is missing.")
        return out

    @app.get("/audits/{audit_id}/result.json")
    def download(audit_id: str, user: Annotated[User, Depends(current_user)]) -> FileResponse:
        owned(audit_id, user)
        path = jobs.store.result_path(audit_id)
        if path is None:
            raise HTTPException(404, "No result for this audit.")
        return FileResponse(path, media_type="application/json", filename=f"audit-{audit_id}.json")

    @app.get("/audits/{audit_id}/report.pdf")
    def report(audit_id: str, user: Annotated[User, Depends(current_user)]) -> Response:
        owned(audit_id, user)
        out = jobs.store.read_result(audit_id)
        if out is None:
            raise HTTPException(404, "No result for this audit.")
        return Response(
            content=build_report_pdf(out),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="audit-{audit_id}.pdf"'},
        )

    return app
