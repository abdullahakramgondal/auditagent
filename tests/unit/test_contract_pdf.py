import json
from pathlib import Path

from data.generator.contract_pdf import locate_rules, read_pages, write_contract_pdf

SPEC_PATH = Path(__file__).resolve().parents[2] / "data" / "specs" / "case_001.json"
SPEC = json.loads(SPEC_PATH.read_text())


def test_pdf_has_expected_page_count_and_text_on_every_page(tmp_path):
    pdf = write_contract_pdf(SPEC, tmp_path / "contract.pdf")
    pages = read_pages(pdf)
    assert len(pages) == SPEC["layout"]["contract_pages"]
    assert all(len(p) > 50 for p in pages)


def test_penalty_clause_is_found_on_target_page(tmp_path):
    pdf = write_contract_pdf(SPEC, tmp_path / "contract.pdf")
    found = locate_rules(SPEC, pdf)
    expected_page = SPEC["layout"]["target_page"]["late_penalty"]
    assert found["late_penalty"]["page"] == expected_page