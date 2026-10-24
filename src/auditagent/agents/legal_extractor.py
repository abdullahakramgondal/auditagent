"""Agent 1: find the audit rules in a contract and prove each one against the contract text."""

import re
from datetime import date
from decimal import Decimal

from pydantic import TypeAdapter, ValidationError

from auditagent.agents.grounding import (
    date_in,
    days_in,
    locate_quote,
    number_in,
    percent_in,
    units_in,
)
from auditagent.agents.legal_forms import (
    LateRulesForm,
    PaymentRulesForm,
    PriceRulesForm,
    VolumeRulesForm,
)
from auditagent.ingestion.chunker import chunk_document
from auditagent.ingestion.embedder import Embedder
from auditagent.ingestion.pdf_parser import normalize_for_match
from auditagent.ingestion.vectorstore import ContractIndex
from auditagent.llm.base import LLMOutputError, LLMProvider, generate_structured
from auditagent.schemas.chunk import Chunk
from auditagent.schemas.contract import ContractRule, ExtractedContract
from auditagent.schemas.document import ParsedDocument
from auditagent.schemas.extraction import AgentOneResult, ExtractionIssue

KINDS = ("late_penalty", "volume_discount", "payment_terms", "unit_price")
TOP_K = 8

# Safety net: if these patterns appear in the retrieved clauses, an empty answer is suspicious.
HINTS = {
    "late_penalty": re.compile(r"\b(late|delay\w*)\b.{0,200}\d+(\.\d+)?\s*%", re.I | re.S),
    "volume_discount": re.compile(r"\bdiscount\b.{0,200}\d+(\.\d+)?\s*%", re.I | re.S),
    "payment_terms": re.compile(r"\bwithin\b.{0,60}\b\d+\b.{0,20}\bdays?\b", re.I | re.S),
    "unit_price": re.compile(r"\bunit\b.{0,120}PKR\s*\d", re.I | re.S),
}

RETRIEVAL_QUERIES = {
    "late_penalty": "penalty or deduction for late delivery of the goods",
    "volume_discount": "discount for ordering a large quantity of units",
    "payment_terms": "invoice payment due within a number of days",
    "unit_price": "Unit Price in PKR per unit, the fixed price per item stated in the contract",
}

FORMS = {
    "late_penalty": LateRulesForm,
    "volume_discount": VolumeRulesForm,
    "payment_terms": PaymentRulesForm,
    "unit_price": PriceRulesForm,
}

SYSTEM = (
    "You read contract clauses and fill in a form. Use only the clauses you are given. "
    "Never guess or invent a rule: if the clauses do not contain the rule, return an empty list. "
    "Copy the quote word for word from the clause text. Answer with JSON only."
)

TASKS = {
    "late_penalty": (
        "Find rules where the VENDOR is penalised for LATE DELIVERY of the goods "
        "(a penalty, deduction or liquidated damages when delivery is after a deadline). "
        "Ignore liability caps, termination rights, and late PAYMENT charges that apply to the Buyer. "
        "mode is flat_percent when one percentage applies once, and per_day_percent when a percentage "
        "applies for each day of delay."
    ),
    "volume_discount": (
        "Find rules that give the Buyer a DISCOUNT when it orders at least a minimum number of units."
    ),
    "payment_terms": (
        "Find rules that say within how many DAYS an invoice must be paid. "
        "Ignore charges for paying late."
    ),
    "unit_price": (
        "Find rules that fix the agreed price PER UNIT of a named item that the invoice must not exceed."
    ),
}

_RULE = TypeAdapter(ContractRule)


def _prompt(kind: str, chunks: list[Chunk]) -> str:
    blocks = "\n\n".join(f"[chunk_id: {c.chunk_id}]\n{c.text}" for c in chunks)
    return (
        f"{TASKS[kind]}\n\nClauses from the contract:\n\n{blocks}\n\n"
        'Return {"rules": [...]} with one entry per rule you found, or {"rules": []} if there is none.'
    )


def _rule_fields(kind: str, form) -> dict:
    if kind == "late_penalty":
        return {
            "clause_type": kind,
            "deadline": form.deadline,
            "mode": form.mode,
            "percent": Decimal(str(form.percent)),
            "cap_percent": None if form.cap_percent is None else Decimal(str(form.cap_percent)),
            "grace_days": form.grace_days,
        }
    if kind == "volume_discount":
        return {
            "clause_type": kind,
            "min_quantity": form.min_quantity,
            "discount_percent": Decimal(str(form.discount_percent)),
        }
    if kind == "payment_terms":
        return {"clause_type": kind, "net_days": form.net_days}
    return {
        "clause_type": kind,
        "item_name": form.item_name,
        "agreed_unit_price": Decimal(str(form.agreed_unit_price)),
    }


def _fact_problems(kind: str, form) -> list[str]:
    """Numbers and dates the model reported must really be written in its own quote, in the right role."""
    quote = form.quote
    problems = []

    def need(label, value, check):
        if not check(value, quote):
            problems.append(f"{label} {value} is not written in the quote")

    if kind == "late_penalty":
        try:
            deadline = date.fromisoformat(form.deadline)
        except ValueError:
            problems.append(f"deadline {form.deadline!r} is not a valid YYYY-MM-DD date")
        else:
            if not date_in(deadline, quote):
                problems.append(f"deadline {form.deadline} is not written in the quote")
        need("percent", form.percent, percent_in)
        if form.cap_percent is not None:
            need("cap_percent", form.cap_percent, percent_in)
        if form.grace_days > 0:
            need("grace_days", form.grace_days, days_in)
    elif kind == "volume_discount":
        need("min_quantity", form.min_quantity, units_in)
        need("discount_percent", form.discount_percent, percent_in)
    elif kind == "payment_terms":
        need("net_days", form.net_days, days_in)
    else:
        if normalize_for_match(form.item_name).lower() not in normalize_for_match(quote).lower():
            problems.append(f"item {form.item_name!r} is not written in the quote")
        need("agreed_unit_price", form.agreed_unit_price, number_in)
    return problems


class LegalExtractor:
    def __init__(self, provider: LLMProvider, embedder: Embedder, top_k: int = TOP_K):
        self._provider = provider
        self._embedder = embedder
        self._top_k = top_k

    def extract(self, doc: ParsedDocument) -> AgentOneResult:
        """Return the verified rules of one contract, plus every proposal we had to refuse."""
        chunks = chunk_document(doc)
        if not chunks:
            return self._result([], [ExtractionIssue(clause_type="all", reason="The contract has no readable text")])

        rules: list = []
        issues: list[ExtractionIssue] = []
        index = ContractIndex(self._embedder, chunks, doc_label=doc.sha256[:12])
        try:
            for kind in KINDS:
                hits = index.search(RETRIEVAL_QUERIES[kind], k=self._top_k)
                try:
                    form = generate_structured(
                        self._provider, SYSTEM, _prompt(kind, [h.chunk for h in hits]), FORMS[kind]
                    )
                except LLMOutputError as exc:
                    issues.append(ExtractionIssue(clause_type=kind, reason=f"Model output unusable: {exc}"))
                    continue
                for item in form.rules:
                    rule, issue = self._verify(kind, item, chunks)
                    if rule is not None:
                        rules.append(rule)
                    if issue is not None:
                        issues.append(issue)
                if not form.rules and any(HINTS[kind].search(h.chunk.text) for h in hits):
                    issues.append(
                        ExtractionIssue(
                            clause_type=kind,
                            reason="Keywords found in the contract but no rule extracted: needs review",
                        )
                    )
        finally:
            index.close()
        return self._result(rules, issues)

    def _verify(self, kind: str, item, chunks: list[Chunk]):
        chunk = locate_quote(chunks, item.quote, item.chunk_id)
        if chunk is None:
            return None, ExtractionIssue(
                clause_type=kind, reason="Quote not found in the contract text", quote=item.quote
            )
        problems = _fact_problems(kind, item)
        if problems:
            return None, ExtractionIssue(clause_type=kind, reason="; ".join(problems), quote=item.quote)
        # The page comes from the parser (where the quote really is), never from the model.
        source = {"page": chunk.page_start, "text": normalize_for_match(item.quote)}
        try:
            return _RULE.validate_python({**_rule_fields(kind, item), "source": source}), None
        except ValidationError as exc:
            return None, ExtractionIssue(
                clause_type=kind,
                reason=f"Rule failed validation: {exc.error_count()} error(s)",
                quote=item.quote,
            )

    def _result(self, rules, issues) -> AgentOneResult:
        return AgentOneResult(
            contract=ExtractedContract(rules=rules), issues=issues, llm_model=self._provider.model
        )