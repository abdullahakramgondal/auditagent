"""Agent 1: find the audit rules in a contract and prove each one against the contract text."""

import re
from decimal import Decimal

from pydantic import TypeAdapter, ValidationError

from auditagent.agents.grounding import (
    DAYS_RE,
    clause_refs,
    date_in,
    days_in,
    is_clause,
    locate_quote,
    number_in,
    parse_written_date,
    percent_count,
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
# The words may come in either order ("a penalty of 8% ... days of delay", "PKR 1,150,000 per unit"),
# and contracts say "volume reduction" or "price adjustment" as well as "discount".
# eval.hint_check measures all of this on every contract without a model.
_PERCENT = r"\d+(?:\.\d+)?\s*%"
_PERCENT_RE = re.compile(_PERCENT)
_DISCOUNT_WORD = r"\b(?:discounts?|rebates?|reductions?|adjustments?)\b"
# Delay or lateness of PAYMENT is a Buyer charge, not a delivery penalty: "late payment", "delays payment",
# "delay in payment" are skipped, and the clause must also talk about delivery.
_LATE_WORD = re.compile(
    r"\b(?:late|delay\w*)\b(?!\s+(?:(?:in|of)\s+)?(?:the\s+)?pay)", re.IGNORECASE
)
_DELIVER_WORD = re.compile(r"\bdeliver\w*\b", re.IGNORECASE)
_DISCOUNT_HINT = re.compile(
    rf"{_DISCOUNT_WORD}.{{0,200}}{_PERCENT}|{_PERCENT}.{{0,100}}{_DISCOUNT_WORD}",
    re.IGNORECASE | re.DOTALL,
)
_UNIT_PRICE_HINT = re.compile(
    r"\bunit\b.{0,120}\bPKR\s*\d|\bPKR\s*\d.{0,80}\bunit\b", re.IGNORECASE | re.DOTALL
)
_INVOICE_WORD = re.compile(r"\binvoices?\b", re.IGNORECASE)
_PAYMENT_WORD = re.compile(r"\b(?:pay\w*|paid|settle\w*|due)\b", re.IGNORECASE)

# Values that may come from the SAME clause as the quote (batch 2): the sentences of the clause
# that talk about the delay (for grace_days) or about the price (for a unit price rule).
_SENTENCE_END = re.compile(r"(?<=[.;])\s+")
_DELAY_CONTEXT = re.compile(r"\b(?:delay\w*|penalt\w*|late)\b", re.IGNORECASE)
_PRICE_CONTEXT = re.compile(r"\b(?:price|unit|rate)\b", re.IGNORECASE)
_PKR_AMOUNT = re.compile(r"\b(?:PKR|Rs\.?)\s*(\d[\d,]*(?:\.\d+)?)", re.IGNORECASE)

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
        "The quote must be ONE continuous passage copied exactly from ONE clause. It must contain every "
        "sentence of that clause that states the percentage, the cap or the grace period; when these sit "
        "in neighbouring sentences, copy them together in the order they appear, and never quote only "
        "the sentence with the percentage. Never join passages from different clauses and never use "
        "'...' in a quote. "
        "deadline_quote is the sentence that states the delivery date. If the date is written in the "
        "same clause as the penalty, copy that sentence there (it may also be part of the quote). If the "
        "penalty clause only refers to the date by a defined term (a capitalised term that another "
        "clause defines), copy the sentence from that other clause."
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


def retrieve(
    index: ContractIndex, kind: str, top_k: int = TOP_K, extra_k: int = EXTRA_K
) -> list[Chunk]:
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
        return bool(
            _LATE_WORD.search(text) and _DELIVER_WORD.search(text) and _PERCENT_RE.search(text)
        )
    if kind == "volume_discount":
        return bool(_DISCOUNT_HINT.search(text))
    if kind == "payment_terms":
        return bool(
            _INVOICE_WORD.search(text) and _PAYMENT_WORD.search(text) and DAYS_RE.search(text)
        )
    return bool(_UNIT_PRICE_HINT.search(text))


def _prompt(kind: str, chunks: list[Chunk]) -> str:
    """The prompt for one clause type: the task, the clauses with their chunk ids, and the answer format."""
    blocks = "\n\n".join(f"[chunk_id: {c.chunk_id}]\n{c.text}" for c in chunks)
    return (
        f"{TASKS[kind]}\n\nClauses from the contract:\n\n{blocks}\n\n"
        'Return {"rules": [...]} with one entry per rule you found, or {"rules": []} if there is none.'
    )


def _effective_cap(form):
    """The cap that counts: only a per-day penalty has one (scope.md: a flat percentage has no cap).

    The model sometimes reports a cap equal to the percentage for a flat penalty (tb_01, tb_04).
    It is ignored: for a flat penalty it changes nothing in the money maths.
    """
    if form.mode == "flat_percent" or form.cap_percent is None:
        return None
    return form.cap_percent


def _rule_fields(kind: str, form) -> dict:
    """The model's form as the fields of a rule (numbers as Decimal, without the source)."""
    if kind == "late_penalty":
        cap = _effective_cap(form)
        return {
            "clause_type": kind,
            # _check_deadline has already proven that this text is a readable date.
            "deadline": parse_written_date(form.deadline),
            "mode": form.mode,
            "percent": Decimal(str(form.percent)),
            "cap_percent": None if cap is None else Decimal(str(cap)),
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


def _sentences_about(clause_text: str, context: re.Pattern) -> list[str]:
    """The sentences of a clause that talk about the given subject (delay, price, ...)."""
    sentences = _SENTENCE_END.split(normalize_for_match(clause_text))
    return [sentence for sentence in sentences if context.search(sentence)]


def _pkr_in(value, text: str) -> bool:
    """True if `value` is written as a rupee amount (PKR 275,000 or Rs. 275,000) in `text`."""
    wanted = Decimal(str(value))
    return any(Decimal(token.replace(",", "")) == wanted for token in _PKR_AMOUNT.findall(text))


def _fact_problems(kind: str, form, clause_text: str = "") -> list[str]:
    """Numbers the model reported must really be written in its own quote, in the right role.

    Two values may also come from the SAME clause as the quote (TODO items 41, 59, 64):
    grace_days from a sentence of the clause that talks about the delay, and the item name and
    the rupee price of a unit price rule from the clause (the quote may be only a part of it).
    (The late-penalty deadline is checked separately: its date may sit in another clause.)
    """
    quote = form.quote
    problems = []

    def need(label, value, check):
        if not check(value, quote):
            problems.append(f"{label} {value} is not written in the quote")

    if kind == "late_penalty":
        need("percent", form.percent, percent_in)
        cap = _effective_cap(form)
        if cap is not None:
            need("cap_percent", cap, percent_in)
            # One number cannot play two roles: a per-day cap equal to the percentage must be
            # written twice in the quote.
            same_number = Decimal(str(cap)) == Decimal(str(form.percent))
            if same_number and percent_count(form.percent, quote) < 2:
                problems.append(
                    f"cap_percent {cap} is the same number as percent "
                    "and is written only once in the quote"
                )
        if form.grace_days > 0:
            written = days_in(form.grace_days, quote) or any(
                days_in(form.grace_days, sentence)
                for sentence in _sentences_about(clause_text, _DELAY_CONTEXT)
            )
            if not written:
                problems.append(
                    f"grace_days {form.grace_days} is not written in the quote "
                    "or in a sentence about the delay of its clause"
                )
    elif kind == "volume_discount":
        need("min_quantity", form.min_quantity, units_in)
        need("discount_percent", form.discount_percent, percent_in)
    elif kind == "payment_terms":
        need("net_days", form.net_days, days_in)
    else:
        name = normalize_for_match(form.item_name).lower()
        if (
            name not in normalize_for_match(quote).lower()
            and name not in normalize_for_match(clause_text).lower()
        ):
            problems.append(f"item {form.item_name!r} is not written in the quote or its clause")
        price = form.agreed_unit_price
        in_clause = any(
            _pkr_in(price, sentence) for sentence in _sentences_about(clause_text, _PRICE_CONTEXT)
        )
        if not (number_in(price, quote) or in_clause):
            problems.append(f"agreed_unit_price {price} is not written in the quote or its clause")
    return problems


def _check_deadline(
    form, chunks: list[Chunk], penalty_chunk: Chunk
) -> tuple[str | None, dict | None]:
    """Prove the deadline date. Returns (problem, source of the date when it is outside the penalty quote).

    The model should answer YYYY-MM-DD, but a written date such as 15 October 2026 is read too
    (parse_written_date, TODO item 60). Reading the format proves nothing: the date must still be
    written in the contract, in one of four cases:
      1. it is written in the penalty quote itself;
      2. it is written in the deadline quote and that passage is in the SAME clause (chunk) as the
         penalty quote, for example the neighbouring sentence "the delivery date is 15 January 2027";
      3. it is written in the deadline quote of ANOTHER clause, and that clause defines a date term
         (for example (the "Delivery Deadline")) which the penalty quote uses;
      4. it is written in the deadline quote of ANOTHER clause, and the penalty quote refers to that
         clause by its number ("the date stated in clause 5.2").
    The deadline quote must really exist in the contract. Cases 3 and 4 keep a decoy clause from
    borrowing a date: the link has to be written in the contract itself.
    """
    deadline = parse_written_date(form.deadline)
    if deadline is None:
        return (
            (
                f"deadline {form.deadline!r} is not a date that can be read "
                "(YYYY-MM-DD, or a written date such as 15 October 2026)"
            ),
            None,
        )
    if date_in(deadline, form.quote):
        return None, None
    missing = f"deadline {form.deadline} is not written in the quote"
    holder = locate_quote(chunks, form.deadline_quote, penalty_chunk.chunk_id)
    if holder is None or not date_in(deadline, form.deadline_quote):
        return missing, None
    source = {"page": holder.page_start, "text": normalize_for_match(form.deadline_quote)}
    if holder.chunk_id == penalty_chunk.chunk_id:
        return None, source
    cites_the_clause = any(is_clause(holder, number) for number in clause_refs(form.quote))
    if shares_defined_term(form.deadline_quote, form.quote) or cites_the_clause:
        return None, source
    return (
        (
            f"{missing}, and the quote neither uses a date term defined where the date is written "
            "nor refers to the clause that holds it"
        ),
        None,
    )


def _canonical(value) -> str:
    """A value of a rule in one spelling, so that 10 and 10.0 or a different case are the same."""
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    return " ".join(str(value).split()).lower()


def _rule_key(rule) -> tuple:
    """What a rule says, without where it was found."""
    values = rule.model_dump(exclude={"source", "deadline_source"})
    return tuple(sorted((name, _canonical(value)) for name, value in values.items()))


def merge_rules(kind: str, rules: list) -> tuple[list, list[ExtractionIssue]]:
    """One rule per thing: the same rule found twice is kept once (TODO item 88).

    The engine of v1 audits one rule per clause type, and one unit price per item. Two DIFFERENT rules
    for the same thing (two net periods, two penalties) cannot be told apart by code: both are dropped
    and the contract goes to review, never a guess.
    """
    distinct: dict[tuple, object] = {}
    for rule in rules:
        distinct.setdefault(_rule_key(rule), rule)
    groups: dict[str, list] = {}
    for rule in distinct.values():
        name = _canonical(rule.item_name) if kind == "unit_price" else kind
        groups.setdefault(name, []).append(rule)
    kept: list = []
    issues: list[ExtractionIssue] = []
    for name, group in groups.items():
        if len(group) == 1:
            kept.append(group[0])
            continue
        thing = f"item {name!r}" if kind == "unit_price" else "the contract"
        issues.append(
            ExtractionIssue(
                clause_type=kind,
                reason=(
                    f"The model returned {len(group)} different {kind} rules for {thing}: "
                    "it cannot be decided which one counts, needs review"
                ),
                quote=group[0].source.text,
            )
        )
    return kept, issues


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
            return self._result(
                [], [ExtractionIssue(clause_type="all", reason="The contract has no readable text")]
            )

        rules: list = []
        issues: list[ExtractionIssue] = []
        index = ContractIndex(self._embedder, chunks, doc_label=doc.sha256[:12])
        try:
            for kind in KINDS:
                shown = retrieve(index, kind, self._top_k)
                try:
                    form = generate_structured(
                        self._provider, SYSTEM, _prompt(kind, shown), FORMS[kind]
                    )
                except LLMOutputError as exc:
                    issues.append(
                        ExtractionIssue(clause_type=kind, reason=f"Model output unusable: {exc}")
                    )
                    continue
                found: list = []
                for item in form.rules:
                    rule, issue = self._verify(kind, item, chunks)
                    if rule is not None:
                        found.append(rule)
                    if issue is not None:
                        issues.append(issue)
                merged, merge_issues = merge_rules(kind, found)
                rules.extend(merged)
                issues.extend(merge_issues)
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
        problems = _fact_problems(kind, item, chunk.text)
        deadline_source = None
        if kind == "late_penalty":
            problem, deadline_source = _check_deadline(item, chunks, chunk)
            if problem:
                problems.insert(0, problem)
        if problems:
            return None, ExtractionIssue(
                clause_type=kind, reason="; ".join(problems), quote=item.quote
            )
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
            contract=ExtractedContract(rules=rules),
            issues=issues,
            llm_model=self._provider.model,
        )
