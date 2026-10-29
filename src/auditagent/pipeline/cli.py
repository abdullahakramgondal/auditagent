"""Run the whole audit on one contract, one purchase order and one invoice.

Usage (project root):  python -m auditagent.pipeline.cli data/generated/gen_010
                       python -m auditagent.pipeline.cli contract.pdf po.pdf invoice.pdf
A folder must hold contract.pdf, po.pdf and invoice.pdf. Sends document text to the configured
LLM provider: use synthetic documents only.
"""

import sys
from decimal import Decimal
from pathlib import Path

from auditagent.agents.commercial_extractor import CommercialExtractor
from auditagent.agents.legal_extractor import LegalExtractor
from auditagent.ingestion.embedder import SentenceTransformerEmbedder
from auditagent.ingestion.pdf_parser import PdfParseError
from auditagent.llm.base import LLMError
from auditagent.llm.factory import build_provider
from auditagent.pipeline.run import AuditReport, audit_files

USAGE = (
    "Usage: python -m auditagent.pipeline.cli <folder>   or   <contract.pdf> <po.pdf> <invoice.pdf>"
)


def _paths(args: list[str]) -> tuple[Path, Path, Path]:
    if len(args) == 1 and Path(args[0]).is_dir():
        folder = Path(args[0])
        return folder / "contract.pdf", folder / "po.pdf", folder / "invoice.pdf"
    if len(args) == 3:
        return Path(args[0]), Path(args[1]), Path(args[2])
    raise SystemExit(USAGE)


def _pkr(value: Decimal | None) -> str:
    return "-" if value is None else f"PKR {value:,.2f}"


def show(report: AuditReport) -> None:
    """Print the result: status, money, every finding with its clause, and the review reasons."""
    result = report.result
    print(f"\nSTATUS: {result.status}   model: {report.llm_model}")
    print(f"  billed total     {_pkr(result.billed_total)}")
    print(f"  correct payable  {_pkr(result.correct_payable)}")
    print(f"  overbilled       {_pkr(result.total_difference)}")
    print(f"\nFINDINGS: {len(result.findings)}")
    for finding in result.findings:
        print(
            f"  [{finding.clause_type}] {_pkr(finding.difference)}  (contract page {finding.source.page})"
        )
        print(f"    {finding.description}")
        print(f"    clause: {finding.source.text}")
    print(f"\nREVIEW REASONS: {len(result.review_reasons)}")
    for reason in result.review_reasons:
        print(f"  - {reason}")


def main() -> None:
    contract, order, invoice = _paths(sys.argv[1:])
    provider = build_provider()
    legal = LegalExtractor(provider, SentenceTransformerEmbedder())
    commercial = CommercialExtractor(provider)
    try:
        report = audit_files(contract, order, invoice, legal, commercial)
    except (PdfParseError, LLMError) as exc:
        raise SystemExit(f"STOPPED: {exc}") from exc
    show(report)


if __name__ == "__main__":
    main()
