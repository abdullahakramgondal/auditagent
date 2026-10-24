"""Agent 1: find the audit rules in a contract and prove each one against the contract text."""

import re
from datetime import date
from decimal import Decimal

from pydantic import TypeAdapter, ValidationError

from auditagent.agents.grounding import (
    DAYS_RE,
    date_in,
    days_in,
    locate_quote,
    number_in,
    percent_in,
    shares_defined_term,
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
TOP_K = 8  # chunks the model sees for the first query of a clause type
EXTRA_K = 3  # new chunks added for each further query of the same clause type

# The first query finds the rule itself. Further queries find clauses the rule depends on:
# a penalty clause often says "after the Delivery Deadline" and the date is written in another clause.
RETRIEVAL_QUERIES = {
    "late_penalty": (
        "penalty or deduction for late delivery of the goods",
        "date by which the Vendor must deliver the goods, the delivery deadline",
    ),
    "volume_discount": ("discount for ordering a large quantity of units",),
    "payment_terms": ("invoice payment due within a number of days",),
    "unit_price": ("Unit Price in PKR per unit, the fixed price per item stated in the contract",),
}

# Safety net: if the model returns nothing but these patterns appear in the clauses it was shown,
# the empty answer is suspicious and must become a review issue, never silence.
# Delay or lateness of PAYMENT is a Buyer charge, not a delivery penalty: "late payment", "delays payment",
# "delay in payment" are skipped.
_LATE_DELIVERY_HINT = re.compile(
    r"\b(?:late|delay\w*)\b(?!\s+(?:(?:in|of)\s+)?(?:the\s+)?pay).{0,200}\d+(?:\.\d+)?\s*%",
    re.I | re.S,
)
_DISCOUNT_HINT = re.compile(r"\bdiscount\b.{0,200}\d+(?:\.\d+)?\s*%", re.I | re.S)
_UNIT_PRICE_HINT = re.compile(r"\bunit\b.{0,120}\bPKR\s*\d", re.I | re.S)
_INVOICE_WORD = re.compile(r"\binvoices?\b", re.I)
_PAYMENT_WORD = re.compile(r"\b(?:pay\w*|paid|settle\w*|due)\b", re.I)

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
        "applies for each day of delay. "
        "The quote must contain EVERY sentence that states a value of the rule: the delivery date, the grace "
        "period, the percentage and the cap. When they are in neighbouring sentences of one clause, copy all "
        "of those sentences together as one passage, in the order they appear in the contract; never quote "
        "only the sentence with the percentage. "
        "If the penalty clause only refers to the date by a defined term (a capitalised term that another "
        "clause defines), copy the sentence that states the date into deadline_quote; otherwise repeat the "
        "quote in deadline_quote."
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


def retrieve(index: ContractIndex, kind: str, top_k: int = TOP_K, extra_k: int = EXTRA_K) -> list[Chunk]:
    """The chunks the model is shown for one clause type: top_k for the first query, then up to
    extra_k new chunks for each further query. Eval and diagnose tools call this same function."""
    first, *further = RETRIEVAL_QUERIES[kind]
    chunks = [hit.chunk for hit in index.search(first, k=top_k)]
    seen = {chunk.chunk_id for chunk in chunks}
    for query in further:
        added = 0
        for hit in index.search(query, k=top_k + extra_k):
            if added == extra_k:
                break
            if hit.chunk.chunk_id not in seen:
                seen.add(hit.chunk.chunk_id)
                chunks.append(hit.chunk)
                added += 1
    return chunks


def hint_fires(kind: str, text: str) -> bool:
    """True if this clause text looks like the rule of this type (used only for the empty-answer safety net)."""
    if kind == "late_penalty":
        return bool(_LATE_DELIVERY_HINT.search(text))
    if kind == "volume_discount":
        return bool(_DISCOUNT_HINT.search(text))
    if kind == "payment_terms":
        return bool(_INVOICE_WORD.search(text) and _PAYMENT_WORD.search(text) and DAYS_RE.search(text))
    return bool(_UNIT_PRICE_HINT.search(text))


def _prompt(kind: str, chunks: list[Chunk]) -> str:
    """The prompt for one clause type: the task, the clauses with their chunk ids, and the answer format."""
    blocks = "\n\n".join(f"[chunk_id: {c.chunk_id}]\n{c.text}" for c in chunks)
    return (
        f"{TASKS[kind]}\n\nClauses from the contract:\n\n{blocks}\n\n"
        'Return {"rules": [...]} with one entry per rule you found, or {"rules": []} if there is none.'
    )


def _rule_fields(kind: str, form) -> dict:
    """The model's form as the fields of a rule (numbers as Decimal, without the source)."""
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
    """Numbers the model reported must really be written in its own quote, in the right role.
    (The late-penalty deadline is checked separately: its date may sit in another clause.)"""
    quote = form.quote
    problems = []

    def need(label, value, check):
        if not check(value, quote):
            problems.append(f"{label} {value} is not written in the quote")

    if kind == "late_penalty":
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


def _check_deadline(form, chunks: list[Chunk]) -> tuple[str | None, dict | None]:
    """Prove the deadline date. Returns (problem, source of the date when it is outside the penalty quote).

    The date is accepted if it is written in the penalty quote itself. Otherwise it must be written in a
    second quote that really exists in the contract AND that quote must define a date term (for example
    (the "Delivery Deadline")) which the penalty quote uses. This keeps decoy clauses from borrowing a date.
    """
    try:
        deadline = date.fromisoformat(form.deadline)
    except ValueError:
        return f"deadline {form.deadline!r} is not a valid YYYY-MM-DD date", None
    if date_in(deadline, form.quote):
        return None, None
    missing = f"deadline {form.deadline} is not written in the quote"
    holder = locate_quote(chunks, form.deadline_quote)
    if holder is None or not date_in(deadline, form.deadline_quote):
        return missing, None
    if not shares_defined_term(form.deadline_quote, form.quote):
        return f"{missing}, and the quote does not use a date term defined where the date is written", None
    return None, {"page": holder.page_start, "text": normalize_for_match(form.deadline_quote)}


class LegalExtractor:
    """Agent 1: reads one contract and returns the rules it can prove, plus every proposal it had to refuse."""

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
                shown = retrieve(index, kind, self._top_k)
                try:
                    form = generate_structured(self._provider, SYSTEM, _prompt(kind, shown), FORMS[kind])
                except LLMOutputError as exc:
                    issues.append(ExtractionIssue(clause_type=kind, reason=f"Model output unusable: {exc}"))
                    continue
                for item in form.rules:
                    rule, issue = self._verify(kind, item, chunks)
                    if rule is not None:
                        rules.append(rule)
                    if issue is not None:
                        issues.append(issue)
                if not form.rules and any(hint_fires(kind, c.text) for c in shown):
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
        """Check one proposed rule against the contract. Returns (rule, None) or (None, issue)."""
        chunk = locate_quote(chunks, item.quote, item.chunk_id)
        if chunk is None:
            return None, ExtractionIssue(
                clause_type=kind, reason="Quote not found in the contract text", quote=item.quote
            )
        problems = _fact_problems(kind, item)
        deadline_source = None
        if kind == "late_penalty":
            problem, deadline_source = _check_deadline(item, chunks)
            if problem:
                problems.insert(0, problem)
        if problems:
            return None, ExtractionIssue(clause_type=kind, reason="; ".join(problems), quote=item.quote)
        # The page comes from the parser (where the quote really is), never from the model.
        fields = {
            **_rule_fields(kind, item),
            "source": {"page": chunk.page_start, "text": normalize_for_match(item.quote)},
        }
        if deadline_source is not None:
            fields["deadline_source"] = deadline_source
        try:
            return _RULE.validate_python(fields), None
        except ValidationError as exc:
            return None, ExtractionIssue(
                clause_type=kind,
                reason=f"Rule failed validation: {exc.error_count()} error(s)",
                quote=item.quote,
            )

    def _result(self, rules, issues) -> AgentOneResult:
        """Wrap the rules and issues together with the name of the model that was used."""
        return AgentOneResult(
            contract=ExtractedContract(rules=rules), issues=issues, llm_model=self._provider.model
        )