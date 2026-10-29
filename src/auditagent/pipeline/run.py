"""The pipeline: a contract, a purchase order and an invoice go in, one AuditReport comes out.

A bad file (PdfParseError) or an unavailable model (LLMError) is NOT turned into a result: it is
raised, so that the API can answer "this file is not usable" or "try again later".
Everything else that cannot be proven becomes a review reason: never a silent COMPLIANT.
"""

from pydantic import BaseModel

from auditagent.agents.commercial_extractor import CommercialExtractor
from auditagent.agents.legal_extractor import LegalExtractor
from auditagent.ingestion.pdf_parser import parse_pdf
from auditagent.rules.cross_check import po_review_reasons
from auditagent.rules.engine import audit_invoice
from auditagent.schemas.audit import AuditResult
from auditagent.schemas.contract import ExtractedContract
from auditagent.schemas.document import ParsedDocument
from auditagent.schemas.extraction import ExtractionIssue
from auditagent.schemas.invoice import InvoiceData, PurchaseOrderData


class AuditReport(BaseModel):
    """The audit result together with the documents it was computed from (for a human to compare)."""

    result: AuditResult
    contract: ExtractedContract
    invoice: InvoiceData | None = None
    purchase_order: PurchaseOrderData | None = None
    llm_model: str


def _reasons(source: str, issues: list[ExtractionIssue]) -> list[str]:
    """The issues of one agent about one document, as review reasons."""
    return [f"{source}: {issue.clause_type}: {issue.reason}" for issue in issues]


def audit_documents(
    contract_doc: ParsedDocument,
    po_doc: ParsedDocument,
    invoice_doc: ParsedDocument,
    legal: LegalExtractor,
    commercial: CommercialExtractor,
) -> AuditReport:
    """Run Agent 1, Agent 2 and the rule engine on three parsed documents."""
    contract_result = legal.extract(contract_doc)
    invoice_result = commercial.extract_invoice(invoice_doc)
    po_result = commercial.extract_purchase_order(po_doc)

    contract = contract_result.contract
    invoice, order = invoice_result.invoice, po_result.purchase_order
    reasons = [
        *_reasons("contract", contract_result.issues),
        *_reasons("invoice", invoice_result.issues),
        *_reasons("purchase order", po_result.issues),
    ]

    if invoice is None:
        reasons.append("The invoice could not be proven from its text, so no amount was checked.")
        result = AuditResult(status="NEEDS_REVIEW", review_reasons=reasons)
    else:
        if order is None:
            reasons.append("The purchase order could not be proven: it was not compared.")
        else:
            reasons += po_review_reasons(contract, invoice, order)
        if not contract.rules:
            reasons.append("No audit rule was found in the contract: nothing could be checked.")
        result = audit_invoice(contract, invoice, reasons)

    return AuditReport(
        result=result,
        contract=contract,
        invoice=invoice,
        purchase_order=order,
        llm_model=contract_result.llm_model,
    )


def audit_files(
    contract_pdf,
    po_pdf,
    invoice_pdf,
    legal: LegalExtractor,
    commercial: CommercialExtractor,
) -> AuditReport:
    """Parse three PDF files and audit them."""
    return audit_documents(
        parse_pdf(contract_pdf), parse_pdf(po_pdf), parse_pdf(invoice_pdf), legal, commercial
    )
