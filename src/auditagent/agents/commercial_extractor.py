"""Agent 2: read an invoice or a purchase order and prove every value against the document text."""

from datetime import date
from decimal import Decimal

from pydantic import ValidationError

from auditagent.agents.commercial_forms import (
    InvoiceForm,
    LineItemForm,
    PurchaseOrderForm,
)
from auditagent.agents.doc_grounding import (
    adjustment_problem,
    date_is_labelled,
    is_written,
    item_problem,
    shows_a_date,
    text_lines,
    total_is_written,
)
from auditagent.llm.base import LLMOutputError, LLMProvider, generate_structured
from auditagent.schemas.document import ParsedDocument
from auditagent.schemas.extraction import ExtractionIssue, InvoiceResult, PurchaseOrderResult
from auditagent.schemas.invoice import InvoiceData, LineItem, PurchaseOrderData

SYSTEM = (
    "You read one commercial document (an invoice or a purchase order) and fill in a form. "
    "Use only the text you are given. Never guess or invent a value. Copy names, numbers and labels "
    "exactly as printed. Dates are asked as YYYY-MM-DD: convert the printed date. Answer with JSON only."
)
INVOICE_TASK = (
    "Fill in the invoice form from the document below. List every line item, and every adjustment: "
    "a discount, credit or charge printed under the items (use an empty list when there is none). "
    "Use null for a delivery date or a due date that the document does not show."
)
PO_TASK = (
    "Fill in the purchase order form from the document below. List every line item. "
    "Use null for a delivery due date that the document does not show."
)


def _issue(field: str, reason: str) -> ExtractionIssue:
    """One issue about one field of the document."""
    return ExtractionIssue(clause_type=field, reason=reason)


def _money(value: float) -> Decimal:
    """A number the model reported as an exact Decimal (read through its text, so 1000000.0 stays 1000000.0)."""
    return Decimal(str(value))


def _prompt(task: str, doc: ParsedDocument) -> str:
    """The prompt: the task, the text of the document, and the answer format."""
    text = "\n".join(page.text for page in doc.pages)
    return f"{task}\n\nDocument text:\n\n{text}\n\nReturn the JSON form."


def _date_issues(field: str, value: str | None, lines: list[str]) -> list[ExtractionIssue]:
    """A date must be valid and written next to its own label. A none must be a date the document lacks."""
    if value is None:
        if shows_a_date(field, lines):
            return [
                _issue(
                    field,
                    f"{field}: the document shows a date next to a label for it but the model "
                    "returned none: needs review",
                )
            ]
        return []
    try:
        day = date.fromisoformat(value)
    except ValueError:
        return [_issue(field, f"{field} {value!r} is not a valid YYYY-MM-DD date")]
    if not date_is_labelled(day, field, lines):
        return [_issue(field, f"{field} {value} is not written on a line labelled for it")]
    return []


def _line_issues(items: list[LineItemForm], lines: list[str]) -> list[ExtractionIssue]:
    """Every item row must be written in the document with its quantity, unit price and amount."""
    issues = []
    for item in items:
        problem = item_problem(
            item.item_name, item.quantity, item.unit_price, item.line_total, lines
        )
        if problem:
            issues.append(_issue("line_items", problem))
    return issues


def _invoice_issues(form: InvoiceForm, lines: list[str]) -> list[ExtractionIssue]:
    """Everything in the invoice form that the document text does not prove."""
    issues = []
    if not is_written(form.invoice_number, lines):
        issues.append(
            _issue("invoice_number", f"invoice number {form.invoice_number!r} is not written")
        )
    for field in ("invoice_date", "delivery_date", "due_date"):
        issues += _date_issues(field, getattr(form, field), lines)
    issues += _line_issues(form.line_items, lines)
    for adjustment in form.adjustments:
        problem = adjustment_problem(adjustment.label, adjustment.amount, lines)
        if problem:
            issues.append(_issue("adjustments", problem))
    if not total_is_written(form.total_amount, lines):
        issues.append(_issue("total_amount", f"total {form.total_amount} is not on a total line"))
    return issues


def _po_issues(form: PurchaseOrderForm, lines: list[str]) -> list[ExtractionIssue]:
    """Everything in the purchase order form that the document text does not prove."""
    issues = []
    if not is_written(form.po_number, lines):
        issues.append(_issue("po_number", f"order number {form.po_number!r} is not written"))
    for field in ("po_date", "delivery_due_date"):
        issues += _date_issues(field, getattr(form, field), lines)
    issues += _line_issues(form.line_items, lines)
    if not total_is_written(form.total_amount, lines):
        issues.append(_issue("total_amount", f"total {form.total_amount} is not on a total line"))
    return issues


def _line_item_fields(items: list[LineItemForm]) -> list[dict]:
    """The rows of the form as fields of the schema (money as Decimal)."""
    return [
        {
            "item_name": item.item_name,
            "quantity": item.quantity,
            "unit_price": _money(item.unit_price),
            "line_total": _money(item.line_total),
        }
        for item in items
    ]


def _line_total_issues(line_items: list[LineItem]) -> list[ExtractionIssue]:
    """A row whose printed amount is not quantity x unit price: the document itself is wrong."""
    issues = []
    for item in line_items:
        expected = item.quantity * item.unit_price
        if expected != item.line_total:
            issues.append(
                _issue(
                    "line_total",
                    f"Row {item.item_name!r}: {item.quantity} x {item.unit_price:,.2f} = "
                    f"{expected:,.2f} but the document shows {item.line_total:,.2f}",
                )
            )
    return issues


def invoice_integrity_issues(invoice: InvoiceData) -> list[ExtractionIssue]:
    """Arithmetic problems printed on the invoice itself: they are findings or review reasons, never errors."""
    issues = _line_total_issues(invoice.line_items)
    expected = sum((item.line_total for item in invoice.line_items), Decimal(0)) + sum(
        (adjustment.amount for adjustment in invoice.adjustments), Decimal(0)
    )
    if expected != invoice.total_amount:
        issues.append(
            _issue(
                "total_amount",
                f"The rows and adjustments add up to {expected:,.2f} "
                f"but the total is {invoice.total_amount:,.2f}",
            )
        )
    return issues


def purchase_order_integrity_issues(order: PurchaseOrderData) -> list[ExtractionIssue]:
    """Arithmetic problems printed on the purchase order itself."""
    issues = _line_total_issues(order.line_items)
    expected = sum((item.line_total for item in order.line_items), Decimal(0))
    if expected != order.total_amount:
        issues.append(
            _issue(
                "total_amount",
                f"The rows add up to {expected:,.2f} but the total is {order.total_amount:,.2f}",
            )
        )
    return issues


class CommercialExtractor:
    """Agent 2: reads an invoice or a purchase order and returns only what the document text proves."""

    def __init__(self, provider: LLMProvider):
        self._provider = provider

    def extract_invoice(self, doc: ParsedDocument) -> InvoiceResult:
        """The verified invoice, or no invoice and the reasons. Printed arithmetic problems are issues."""
        model = self._provider.model
        if not doc.has_text:
            return InvoiceResult(
                issues=[_issue("document", "The invoice has no readable text")], llm_model=model
            )
        try:
            form = generate_structured(
                self._provider, SYSTEM, _prompt(INVOICE_TASK, doc), InvoiceForm
            )
        except LLMOutputError as exc:
            return InvoiceResult(
                issues=[_issue("document", f"Model output unusable: {exc}")], llm_model=model
            )
        issues = _invoice_issues(form, text_lines("\n".join(p.text for p in doc.pages)))
        if issues:
            return InvoiceResult(issues=issues, llm_model=model)
        try:
            invoice = InvoiceData.model_validate(
                {
                    "invoice_number": form.invoice_number,
                    "invoice_date": form.invoice_date,
                    "delivery_date": form.delivery_date,
                    "due_date": form.due_date,
                    "line_items": _line_item_fields(form.line_items),
                    "adjustments": [
                        {"label": a.label, "amount": _money(a.amount)} for a in form.adjustments
                    ],
                    "total_amount": _money(form.total_amount),
                }
            )
        except ValidationError as exc:
            reason = f"Invoice failed validation: {exc.error_count()} error(s)"
            return InvoiceResult(issues=[_issue("document", reason)], llm_model=model)
        return InvoiceResult(
            invoice=invoice, issues=invoice_integrity_issues(invoice), llm_model=model
        )

    def extract_purchase_order(self, doc: ParsedDocument) -> PurchaseOrderResult:
        """The verified purchase order, or no order and the reasons. Printed arithmetic problems are issues."""
        model = self._provider.model
        if not doc.has_text:
            return PurchaseOrderResult(
                issues=[_issue("document", "The purchase order has no readable text")],
                llm_model=model,
            )
        try:
            form = generate_structured(
                self._provider, SYSTEM, _prompt(PO_TASK, doc), PurchaseOrderForm
            )
        except LLMOutputError as exc:
            return PurchaseOrderResult(
                issues=[_issue("document", f"Model output unusable: {exc}")], llm_model=model
            )
        issues = _po_issues(form, text_lines("\n".join(p.text for p in doc.pages)))
        if issues:
            return PurchaseOrderResult(issues=issues, llm_model=model)
        try:
            order = PurchaseOrderData.model_validate(
                {
                    "po_number": form.po_number,
                    "po_date": form.po_date,
                    "delivery_due_date": form.delivery_due_date,
                    "line_items": _line_item_fields(form.line_items),
                    "total_amount": _money(form.total_amount),
                }
            )
        except ValidationError as exc:
            reason = f"Purchase order failed validation: {exc.error_count()} error(s)"
            return PurchaseOrderResult(issues=[_issue("document", reason)], llm_model=model)
        return PurchaseOrderResult(
            purchase_order=order, issues=purchase_order_integrity_issues(order), llm_model=model
        )
