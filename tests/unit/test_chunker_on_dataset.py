import random

from auditagent.ingestion.chunker import chunk_document
from auditagent.ingestion.pdf_parser import normalize_for_match, parse_pdf
from data.generator.contract_pdf import write_contract_pdf
from data.generator.templates import FILLERS, VARIANTS, render_clause

RULES = [
    {
        "clause_type": "late_penalty",
        "deadline": "2026-10-15",
        "mode": "per_day_percent",
        "percent": "1",
        "cap_percent": "10",
        "grace_days": 3,
    },
    {"clause_type": "volume_discount", "min_quantity": 25, "discount_percent": "5"},
    {
        "clause_type": "unit_price",
        "item_name": "Dell PowerEdge R750 Server",
        "agreed_unit_price": "1500000",
    },
    {"clause_type": "payment_terms", "net_days": 45},
]


def test_every_rule_clause_lands_in_exactly_one_chunk_on_its_page(tmp_path):
    for n in range(1, 13):
        rng = random.Random(n)
        pages = rng.choice([3, 4, 6, 10, 18, 20])
        spec = {
            "case_id": f"t{n}",
            "seed": n,
            "buyer": "Buyer Co",
            "vendor": "Vendor Co",
            "layout": {
                "contract_pages": pages,
                "wording_variant": rng.choice(VARIANTS),
                "filler_clauses": rng.sample(list(FILLERS), rng.randint(2, 5)),
                "target_page": {r["clause_type"]: rng.randint(2, pages) for r in RULES},
            },
            "rules": RULES,
        }
        doc = parse_pdf(write_contract_pdf(spec, tmp_path / f"t{n}.pdf"))
        chunks = chunk_document(doc)
        assert all("SUPPLY AGREEMENT" not in c.text for c in chunks), n
        assert len({c.chunk_id for c in chunks}) == len(chunks), n
        for rule in spec["rules"]:
            quote = normalize_for_match(render_clause(rule, spec["layout"]["wording_variant"]))
            holders = [c for c in chunks if quote in normalize_for_match(c.text)]
            target = spec["layout"]["target_page"][rule["clause_type"]]
            assert len(holders) == 1, (n, rule["clause_type"], len(holders))
            assert holders[0].page_start == holders[0].page_end == target, (n, rule["clause_type"])
