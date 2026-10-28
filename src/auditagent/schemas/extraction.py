from pydantic import BaseModel, Field

from auditagent.schemas.contract import ExtractedContract
from auditagent.schemas.invoice import InvoiceData, PurchaseOrderData


class ExtractionIssue(BaseModel):
    """A value the model proposed but we refused, or a problem we want a human to see.

    clause_type names the part concerned: a clause type for Agent 1 (late_penalty, unit_price, ...)
    or a field of the document for Agent 2 (invoice_date, line_items, total_amount, ...).
    """

    clause_type: str
    reason: str = Field(min_length=1)
    quote: str = ""


class AgentOneResult(BaseModel):
    """Everything Agent 1 returns for one contract."""

    contract: ExtractedContract
    issues: list[ExtractionIssue] = Field(default_factory=list)
    llm_model: str


class InvoiceResult(BaseModel):
    """Everything Agent 2 returns for one invoice.

    invoice is None when a value could not be proven against the document text: the issues say which.
    When invoice is set, the issues may still list arithmetic problems printed on the invoice itself.
    """

    invoice: InvoiceData | None = None
    issues: list[ExtractionIssue] = Field(default_factory=list)
    llm_model: str


class PurchaseOrderResult(BaseModel):
    """Everything Agent 2 returns for one purchase order (same rules as InvoiceResult)."""

    purchase_order: PurchaseOrderData | None = None
    issues: list[ExtractionIssue] = Field(default_factory=list)
    llm_model: str
