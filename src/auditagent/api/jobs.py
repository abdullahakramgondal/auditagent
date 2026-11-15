"""Audit jobs: files on disk, a state per job, and one worker that runs the pipeline."""

import logging
import os
import re
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from auditagent.api.schemas import AuditOut, ErrorKind, JobInfo, to_audit_out
from auditagent.ingestion.pdf_parser import PdfParseError
from auditagent.llm.base import LLMError, LLMTransientError
from auditagent.pipeline.run import AuditReport

logger = logging.getLogger(__name__)

FILE_NAMES = {"contract": "contract.pdf", "purchase_order": "po.pdf", "invoice": "invoice.pdf"}
_ID = re.compile(r"^[0-9a-f]{32}$")

# (contract pdf, purchase order pdf, invoice pdf, provider name, model name) -> the pipeline report
Runner = Callable[[Path, Path, Path, str | None, str | None], AuditReport]


class JobStore:
    """One folder per audit: the three PDFs, job.json and result.json."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def folder(self, audit_id: str) -> Path | None:
        """The folder of an audit, or None if the id is not one of ours or does not exist."""
        if not _ID.match(audit_id):
            return None
        path = self.root / audit_id
        return path if path.is_dir() else None

    def create(self, audit_id: str) -> Path:
        path = self.root / audit_id
        path.mkdir(parents=True)
        return path

    @staticmethod
    def _write(path: Path, text: str) -> None:
        """Write a file in one step, so that a reader never sees half of it."""
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)

    def write_info(self, info: JobInfo) -> None:
        folder = self.folder(info.audit_id)
        if folder is not None:
            self._write(folder / "job.json", info.model_dump_json(indent=2))

    def read_info(self, audit_id: str) -> JobInfo | None:
        folder = self.folder(audit_id)
        path = None if folder is None else folder / "job.json"
        if path is None or not path.is_file():
            return None
        return JobInfo.model_validate_json(path.read_text(encoding="utf-8"))

    def write_result(self, out: AuditOut) -> None:
        folder = self.folder(out.audit_id)
        if folder is not None:
            self._write(folder / "result.json", out.model_dump_json(indent=2))

    def result_path(self, audit_id: str) -> Path | None:
        folder = self.folder(audit_id)
        path = None if folder is None else folder / "result.json"
        return path if path is not None and path.is_file() else None

    def read_result(self, audit_id: str) -> AuditOut | None:
        path = self.result_path(audit_id)
        return None if path is None else AuditOut.model_validate_json(path.read_text("utf-8"))

    def list_infos(self) -> list[JobInfo]:
        """Every job, newest first."""
        if not self.root.is_dir():
            return []
        infos = [self.read_info(path.name) for path in self.root.iterdir() if path.is_dir()]
        found = [info for info in infos if info is not None]
        return sorted(found, key=lambda info: info.created_at, reverse=True)


class JobManager:
    """Starts audit jobs and runs them one at a time (RAM and the rate limit allow no more)."""

    def __init__(self, store: JobStore, runner: Runner, executor=None):
        self.store = store
        self.runner = runner
        self.executor = executor or ThreadPoolExecutor(max_workers=1)

    def submit(self, pdfs: dict[str, bytes], provider: str | None, model: str | None) -> JobInfo:
        """Save the three PDFs, record the job as queued and hand it to the worker."""
        audit_id = uuid.uuid4().hex
        folder = self.store.create(audit_id)
        for key, name in FILE_NAMES.items():
            (folder / name).write_bytes(pdfs[key])
        info = JobInfo(
            audit_id=audit_id,
            state="queued",
            created_at=datetime.now(UTC),
            provider=provider,
            model=model,
        )
        self.store.write_info(info)
        self.executor.submit(self._run, audit_id)
        return info

    def _fail(self, info: JobInfo, kind: ErrorKind, message: str) -> None:
        info.state = "failed"
        info.error_kind = kind
        info.error = message
        self.store.write_info(info)

    def _run(self, audit_id: str) -> None:
        info = self.store.read_info(audit_id)
        folder = self.store.folder(audit_id)
        if info is None or folder is None:
            return
        info.state = "running"
        self.store.write_info(info)
        started = time.perf_counter()
        try:
            report = self.runner(
                folder / FILE_NAMES["contract"],
                folder / FILE_NAMES["purchase_order"],
                folder / FILE_NAMES["invoice"],
                info.provider,
                info.model,
            )
        except PdfParseError as exc:
            self._fail(info, "bad_file", f"One of the files cannot be used: {exc}")
        except LLMTransientError:
            message = "The language model service is busy. Try again in a few minutes."
            self._fail(info, "provider_unavailable", message)
        except LLMError as exc:
            self._fail(info, "internal", str(exc))
        except Exception:
            logger.exception("audit %s failed", audit_id)
            self._fail(info, "internal", "Unexpected error while auditing. See the server log.")
        else:
            out = to_audit_out(
                audit_id, info.created_at, report, round(time.perf_counter() - started, 1)
            )
            self.store.write_result(out)  # the result first: state "done" means that it exists
            info.state = "done"
            info.status = out.status
            info.total_difference = out.total_difference
            info.llm_model = out.llm_model
            self.store.write_info(info)
