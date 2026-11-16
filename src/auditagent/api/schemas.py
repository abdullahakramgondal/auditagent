"""What the API returns. These shapes are the contract with any front end."""

import re
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from auditagent.pipeline.run import AuditReport
from auditagent.schemas.audit import AuditStatus, Finding
from auditagent.schemas.contract import ExtractedContract
from auditagent.schemas.invoice import InvoiceData, PurchaseOrderData

JobState = Literal["queued", "running", "done", "failed"]
ErrorKind = Literal["bad_file", "provider_unavailable", "internal"]
ReasonSource = Literal["contract", "invoice", "purchase_order", "audit"]

# The agents write their issues as "<document>: <field>: <reason>".
_REASON = re.compile(r"^(contract|invoice|purchase order): (\w+): (.*)$", re.DOTALL)


class ReviewReason(BaseModel):
    """One thing that the system could not prove, in a form a screen can group."""

    source: ReasonSource
    field: str
    reason: str


class JobInfo(BaseModel):
    """The state of one audit job (also one row of the history)."""

    audit_id: str
    state: JobState
    created_at: datetime
    provider: str | None = None
    model: str | None = None
    error: str | None = None
    error_kind: ErrorKind | None = None
    status: AuditStatus | None = None
    total_difference: Decimal | None = None
    llm_model: str | None = None


class Submitted(BaseModel):
    audit_id: str


class AuditOut(BaseModel):
    """The finished audit: the verdict, the money, the evidence and the documents that were read.

    The amounts are None when no invoice could be proven. amounts_provisional is True when the
    amounts exist but a review reason says that a rule or a document could not be proven, so the
    amounts may be incomplete.
    """

    audit_id: str
    created_at: datetime
    status: AuditStatus
    billed_total: Decimal | None
    correct_payable: Decimal | None
    total_difference: Decimal | None
    amounts_provisional: bool
    findings: list[Finding]
    review_reasons: list[ReviewReason]
    contract: ExtractedContract
    invoice: InvoiceData | None
    purchase_order: PurchaseOrderData | None
    llm_model: str
    seconds: float


def reason_out(text: str) -> ReviewReason:
    """A review reason from the pipeline as an object with its source and field."""
    match = _REASON.match(text)
    if match:
        source = match.group(1).replace(" ", "_")
        return ReviewReason(source=source, field=match.group(2), reason=match.group(3))
    return ReviewReason(source="audit", field="", reason=text)


def to_audit_out(
    audit_id: str, created_at: datetime, report: AuditReport, seconds: float
) -> AuditOut:
    """The API shape of a pipeline report."""
    result = report.result
    return AuditOut(
        audit_id=audit_id,
        created_at=created_at,
        status=result.status,
        billed_total=result.billed_total,
        correct_payable=result.correct_payable,
        total_difference=result.total_difference,
        amounts_provisional=result.billed_total is not None and bool(result.review_reasons),
        findings=result.findings,
        review_reasons=[reason_out(text) for text in result.review_reasons],
        contract=report.contract,
        invoice=report.invoice,
        purchase_order=report.purchase_order,
        llm_model=report.llm_model,
        seconds=seconds,
    )


class AuditSummary(BaseModel):
    """The numbers of the dashboard. The backend counts and adds; the front end never adds money."""

    total: int
    in_progress: int
    failed: int
    compliant: int
    non_compliant: int
    needs_review: int
    total_difference: Decimal


def summarize(infos: list[JobInfo]) -> AuditSummary:
    """Count the audits and add up the money found. Only finished audits have a verdict."""
    done = [info for info in infos if info.state == "done"]
    return AuditSummary(
        total=len(infos),
        in_progress=sum(info.state in ("queued", "running") for info in infos),
        failed=sum(info.state == "failed" for info in infos),
        compliant=sum(info.status == "COMPLIANT" for info in done),
        non_compliant=sum(info.status == "NON_COMPLIANT" for info in done),
        needs_review=sum(info.status == "NEEDS_REVIEW" for info in done),
        total_difference=sum(
            (info.total_difference for info in done if info.total_difference is not None),
            Decimal(0),
        ),
    )
