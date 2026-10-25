import json
from pathlib import Path

from data.generator.build_case import build_case

SPEC_PATH = Path(__file__).resolve().parents[2] / "data" / "specs" / "case_001.json"


def test_build_case_creates_all_files(tmp_path):
    out = build_case(SPEC_PATH, tmp_path)
    for name in ("contract.pdf", "po.pdf", "invoice.pdf", "expected.json"):
        assert (out / name).exists()
    expected = json.loads((out / "expected.json").read_text())
    assert expected["status"] == "NON_COMPLIANT"
    assert expected["rule_sources"]["late_penalty"]["page"] == 4
