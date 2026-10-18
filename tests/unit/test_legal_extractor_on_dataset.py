import json
import random
from datetime import date
from decimal import Decimal

from auditagent.agents.legal_extractor import KINDS, LegalExtractor
from auditagent.ingestion.embedder import HashingEmbedder
from auditagent.ingestion.pdf_parser import normalize_for_match, parse_pdf
from auditagent.llm.fake import ScriptedProvider
from auditagent.schemas.contract import (
    LatePenaltyRule,
    PaymentTermsRule,
    Source,
    UnitPriceRule,
    VolumeDiscountRule,
)
from data.generator.contract_pdf import write_contract_pdf
from data.generator.templates import FILLERS, VARIANTS, render_clause

RULES = [
    {"clause_type": "late_penalty", "deadline": "2026-10-15", "mode": "per_day_percent",
     "percent": "1", "cap_percent": "10", "grace_days": 3},
    {"clause_type": "volume_discount", "min_quantity": 25, "discount_percent": "5"},
    {"clause_type": "unit_price", "item_name": "Dell PowerEdge R750 Server", "agreed_unit_price": "1500000"},
    {"clause_type": "payment_terms", "net_days": 45},
]


def ideal_form(rule, quote):
    """What a perfect model would answer for this rule (chunk_id is deliberately wrong)."""
    base = {"quote": quote, "chunk_id": "wrong-id"}
    kind = rule["clause_type"]
    if kind == "late_penalty":
        cap = rule.get("cap_percent")
        return {**base, "deadline": rule["deadline"], "mode": rule["mode"], "percent": float(rule["percent"]),
                "cap_percent": None if cap is None else float(cap), "grace_days": rule.get("grace_days", 0)}
    if kind == "volume_discount":
        return {**base, "min_quantity": rule["min_quantity"], "discount_percent": float(rule["discount_percent"])}
    if kind == "payment_terms":
        return {**base, "net_days": rule["net_days"]}
    return {**base, "item_name": rule["item_name"], "agreed_unit_price": float(rule["agreed_unit_price"])}


def expected_rule(rule, quote, page):
    source = Source(page=page, text=normalize_for_match(quote))
    kind = rule["clause_type"]
    if kind == "late_penalty":
        cap = rule.get("cap_percent")
        return LatePenaltyRule(deadline=date.fromisoformat(rule["deadline"]), mode=rule["mode"],
                               percent=Decimal(rule["percent"]),
                               cap_percent=None if cap is None else Decimal(cap),
                               grace_days=rule.get("grace_days", 0), source=source)
    if kind == "volume_discount":
        return VolumeDiscountRule(min_quantity=rule["min_quantity"],
                                  discount_percent=Decimal(rule["discount_percent"]), source=source)
    if kind == "payment_terms":
        return PaymentTermsRule(net_days=rule["net_days"], source=source)
    return UnitPriceRule(item_name=rule["item_name"], agreed_unit_price=Decimal(rule["agreed_unit_price"]),
                         source=source)


def test_a_perfect_model_is_reproduced_exactly_on_generated_contracts(tmp_path):
    """Plumbing check (parse, chunk, retrieve, prompt, verify, page) with a scripted perfect model."""
    for n in range(1, 13):
        rng = random.Random(n)
        pages = rng.choice([3, 4, 6, 10, 18, 20])
        spec = {
            "case_id": f"t{n}", "seed": n, "buyer": "Buyer Co", "vendor": "Vendor Co",
            "layout": {
                "contract_pages": pages,
                "wording_variant": rng.choice(VARIANTS),
                "filler_clauses": rng.sample(list(FILLERS), rng.randint(2, 5)),
                "target_page": {r["clause_type"]: rng.randint(2, pages) for r in RULES},
            },
            "rules": RULES,
        }
        doc = parse_pdf(write_contract_pdf(spec, tmp_path / f"t{n}.pdf"))
        variant = spec["layout"]["wording_variant"]
        quotes = {r["clause_type"]: render_clause(r, variant) for r in RULES}

        replies = []
        for kind in KINDS:
            forms = [ideal_form(r, quotes[kind]) for r in RULES if r["clause_type"] == kind]
            replies.append(json.dumps({"rules": forms}))

        result = LegalExtractor(ScriptedProvider(replies), HashingEmbedder()).extract(doc)
        expected = [
            expected_rule(next(r for r in RULES if r["clause_type"] == kind), quotes[kind],
                          spec["layout"]["target_page"][kind])
            for kind in KINDS
        ]
        assert result.issues == [], n
        assert result.contract.rules == expected, n