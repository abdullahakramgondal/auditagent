"""Run Agent 1 on one contract PDF and print what it found.

Usage (project root):  python -m auditagent.agents.cli data/generated/gen_010/contract.pdf
Sends clause text to the configured LLM provider: use synthetic contracts only.
"""

import sys

from auditagent.agents.legal_extractor import LegalExtractor
from auditagent.ingestion.embedder import SentenceTransformerEmbedder
from auditagent.ingestion.pdf_parser import parse_pdf
from auditagent.llm.factory import build_provider


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m auditagent.agents.cli <contract.pdf>")
    doc = parse_pdf(sys.argv[1])
    extractor = LegalExtractor(build_provider(), SentenceTransformerEmbedder())
    result = extractor.extract(doc)
    print(f"model: {result.llm_model}   pages: {doc.page_count}")
    print(f"\nRULES FOUND: {len(result.contract.rules)}")
    for rule in result.contract.rules:
        print(f"  [{rule.clause_type}] page {rule.source.page}")
        print("   ", rule.model_dump(mode="json", exclude={"source"}))
        print("    quote:", rule.source.text)
    print(f"\nREFUSED / ISSUES: {len(result.issues)}")
    for issue in result.issues:
        print(f"  [{issue.clause_type}] {issue.reason}")
        if issue.quote:
            print("    quote:", issue.quote)


if __name__ == "__main__":
    main()
