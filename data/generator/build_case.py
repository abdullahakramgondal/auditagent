"""Build contract, PO, invoice PDFs and expected.json for each spec."""

import json
from pathlib import Path

from data.generator.commercial_pdf import write_invoice_pdf, write_po_pdf
from data.generator.contract_pdf import locate_rules, write_contract_pdf

ROOT = Path(__file__).resolve().parents[2]


def build_case(spec_path, out_root=None) -> Path:
    spec = json.loads(Path(spec_path).read_text())
    out_root = Path(out_root) if out_root else ROOT / "data" / "generated"
    out = out_root / spec["case_id"]

    contract = write_contract_pdf(spec, out / "contract.pdf")
    write_po_pdf(spec, out / "po.pdf")
    write_invoice_pdf(spec, out / "invoice.pdf")

    located = locate_rules(spec, contract)
    missing = [k for k, v in located.items() if v["page"] is None]
    if missing:
        raise ValueError(f"Rules not found in rendered PDF: {missing}")

    expected = {**spec["expected"], "rule_sources": located}
    (out / "expected.json").write_text(json.dumps(expected, indent=2))
    return out


def main() -> None:
    for spec_path in sorted((ROOT / "data" / "specs").glob("*.json")):
        print("built", build_case(spec_path))


if __name__ == "__main__":
    main()