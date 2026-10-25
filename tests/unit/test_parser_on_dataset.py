import json

from auditagent.ingestion.pdf_parser import normalize_for_match, parse_pdf
from data.generator.build_case import build_case
from data.generator.spec_generator import generate_all


def test_parser_reproduces_the_answer_key_for_every_case(tmp_path):
    for spec in generate_all():
        spec_path = tmp_path / f"{spec['case_id']}.json"
        spec_path.write_text(json.dumps(spec))
        out = build_case(spec_path, tmp_path / "out")
        expected = json.loads((out / "expected.json").read_text())
        case = spec["case_id"]

        contract = parse_pdf(out / "contract.pdf")
        assert contract.page_count == spec["layout"]["contract_pages"], case
        assert contract.warnings == [], case
        for kind, src in expected["rule_sources"].items():
            quote = normalize_for_match(src["text"])
            hits = [p.number for p in contract.pages if quote in normalize_for_match(p.text)]
            assert hits == [src["page"]], (case, kind, hits)

        invoice = parse_pdf(out / "invoice.pdf")
        po = parse_pdf(out / "po.pdf")
        assert spec["invoice"]["invoice_number"] in invoice.page_text(1), case
        assert spec["purchase_order"]["po_number"] in po.page_text(1), case
        assert invoice.warnings == [] and po.warnings == [], case
