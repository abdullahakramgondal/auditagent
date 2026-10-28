"""Run Agent 2 on the invoice and the purchase order of one generated case and show what it found.

Run:  python -m eval.agent2_try gen_010
      python -m eval.agent2_try gen_010 --provider ollama
Sends the text of two synthetic documents to the LLM provider. The full evaluation comes later.
"""

import argparse
import json
import tempfile
from pathlib import Path

from auditagent.agents.commercial_extractor import CommercialExtractor
from auditagent.config import get_settings
from auditagent.ingestion.pdf_parser import parse_pdf
from auditagent.llm.factory import build_provider
from auditagent.schemas.invoice import InvoiceData, PurchaseOrderData
from data.generator.commercial_pdf import write_invoice_pdf, write_po_pdf

ROOT = Path(__file__).resolve().parents[1]


def show(title: str, data, expected, issues) -> None:
    """Print one document: the data, whether it equals the answer key, and every issue."""
    print(f"\n== {title}")
    if data is None:
        print("NOT EXTRACTED")
    else:
        print(json.dumps(data.model_dump(mode="json"), indent=2))
        print("MATCHES THE ANSWER KEY" if data == expected else "DIFFERS FROM THE ANSWER KEY")
    for issue in issues:
        print(f"   issue [{issue.clause_type}] {issue.reason}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("case_id", help="for example gen_010 (a file in data/specs)")
    parser.add_argument("--provider", choices=["gemini", "ollama"], default=None)
    args = parser.parse_args()

    spec = json.loads((ROOT / "data" / "specs" / f"{args.case_id}.json").read_text())
    settings = get_settings()
    if args.provider:
        settings = settings.model_copy(update={"llm_provider": args.provider})
    extractor = CommercialExtractor(build_provider(settings))
    layout = spec.get("layout", {}).get("doc_variant", 1)
    print(f"{args.case_id}: layout {layout}, model {extractor._provider.model}")

    with tempfile.TemporaryDirectory() as tmp:
        invoice_pdf = write_invoice_pdf(spec, Path(tmp) / "invoice.pdf")
        po_pdf = write_po_pdf(spec, Path(tmp) / "po.pdf")
        invoice = extractor.extract_invoice(parse_pdf(invoice_pdf))
        order = extractor.extract_purchase_order(parse_pdf(po_pdf))

    show("INVOICE", invoice.invoice, InvoiceData.model_validate(spec["invoice"]), invoice.issues)
    show(
        "PURCHASE ORDER",
        order.purchase_order,
        PurchaseOrderData.model_validate(spec["purchase_order"]),
        order.issues,
    )


if __name__ == "__main__":
    main()
