"""The HTTP API: upload three PDFs, poll the job, read the result.

Run (project root):  uvicorn auditagent.api.app:create_app --factory --reload
Interactive docs:    http://127.0.0.1:8000/docs
Environment: AUDITAGENT_JOBS_DIR (default data/jobs), AUDITAGENT_CORS_ORIGINS (comma separated).
Synthetic or test documents only: the text of the documents goes to the chosen model.
"""

import os
import re
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from auditagent.api.jobs import JobManager, JobStore
from auditagent.api.runner import run_audit
from auditagent.api.schemas import AuditOut, JobInfo, Submitted

MAX_BYTES = 10 * 1024 * 1024
PROVIDERS = ("gemini", "ollama")
_MODEL_NAME = re.compile(r"^[A-Za-z0-9._:/-]{1,60}$")


def default_manager() -> JobManager:
    root = Path(os.environ.get("AUDITAGENT_JOBS_DIR", "data/jobs"))
    return JobManager(JobStore(root), run_audit)


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


def create_app(manager: JobManager | None = None) -> FastAPI:
    """The application. Tests pass a manager with a fake runner."""
    jobs = manager or default_manager()
    app = FastAPI(title="AuditAgent AI", version="0.1.0")
    origins = os.environ.get("AUDITAGENT_CORS_ORIGINS", "http://localhost:5173")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in origins.split(",") if origin.strip()],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/audits", status_code=202, response_model=Submitted)
    async def start_audit(
        contract: Annotated[UploadFile, File()],
        purchase_order: Annotated[UploadFile, File()],
        invoice: Annotated[UploadFile, File()],
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
        info = jobs.submit(pdfs, provider or None, model or None)
        return Submitted(audit_id=info.audit_id)

    @app.get("/audits", response_model=list[JobInfo])
    def history() -> list[JobInfo]:
        return jobs.store.list_infos()

    @app.get("/audits/{audit_id}", response_model=JobInfo)
    def job_state(audit_id: str) -> JobInfo:
        info = jobs.store.read_info(audit_id)
        if info is None:
            raise HTTPException(404, "Unknown audit.")
        return info

    @app.get("/audits/{audit_id}/result", response_model=AuditOut)
    def result(audit_id: str) -> AuditOut:
        info = jobs.store.read_info(audit_id)
        if info is None:
            raise HTTPException(404, "Unknown audit.")
        if info.state != "done":
            raise HTTPException(409, info.error or f"The audit is {info.state}.")
        out = jobs.store.read_result(audit_id)
        if out is None:
            raise HTTPException(500, "The result file is missing.")
        return out

    @app.get("/audits/{audit_id}/result.json")
    def download(audit_id: str) -> FileResponse:
        path = jobs.store.result_path(audit_id)
        if path is None:
            raise HTTPException(404, "No result for this audit.")
        return FileResponse(path, media_type="application/json", filename=f"audit-{audit_id}.json")

    return app
