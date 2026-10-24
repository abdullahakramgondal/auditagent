"""Find out why a rule was missed: was the right clause retrieved, and what does the model answer?

Run:  python -m eval.diagnose tb_04 unit_price --needle "275,000"            (retrieval only, no model call)
      python -m eval.diagnose tb_04 unit_price --needle "275,000" --ask      (also one model call, raw answer)
--needle is any text that appears in the clause the rule should come from.
Tier B contracts only (data/tier_b/pdf). Sends clause text to the LLM when --ask is used.
"""

import argparse
from pathlib import Path

from auditagent.agents.legal_extractor import FORMS, RETRIEVAL_QUERIES, SYSTEM, TOP_K, _prompt
from auditagent.ingestion.chunker import chunk_document
from auditagent.ingestion.embedder import Embedder, SentenceTransformerEmbedder
from auditagent.ingestion.pdf_parser import normalize_for_match, parse_pdf
from auditagent.ingestion.vectorstore import ContractIndex
from auditagent.llm.factory import build_provider

ROOT = Path(__file__).resolve().parents[1]


def retrieval_report(doc, kind: str, needle: str, embedder: Embedder, top_k: int = TOP_K) -> dict:
    """Rank every chunk for this clause type and say where the chunks holding `needle` landed."""
    chunks = chunk_document(doc)
    index = ContractIndex(embedder, chunks, doc_label=doc.sha256[:12])
    try:
        ranking = index.search(RETRIEVAL_QUERIES[kind], k=len(chunks))
    finally:
        index.close()
    wanted = normalize_for_match(needle).lower()
    rows = [(rank, hit.chunk, wanted in normalize_for_match(hit.chunk.text).lower())
            for rank, hit in enumerate(ranking, start=1)]
    return {
        "chunk_count": len(chunks),
        "top": rows[:top_k],
        "needle_ranks": [rank for rank, _, found in rows if found],
        "prompt_chunks": [chunk for _, chunk, _ in rows[:top_k]],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("case_id")
    parser.add_argument("kind", choices=sorted(RETRIEVAL_QUERIES))
    parser.add_argument("--needle", required=True)
    parser.add_argument("--ask", action="store_true")
    args = parser.parse_args()

    doc = parse_pdf(ROOT / "data" / "tier_b" / "pdf" / f"{args.case_id}.pdf")
    report = retrieval_report(doc, args.kind, args.needle, SentenceTransformerEmbedder())

    print(f"{args.case_id} / {args.kind}: {report['chunk_count']} chunks. Query: {RETRIEVAL_QUERIES[args.kind]!r}\n")
    print(f"TOP {len(report['top'])} CHUNKS SENT TO THE MODEL")
    for rank, chunk, found in report["top"]:
        mark = "   <== contains the needle" if found else ""
        print(f"  #{rank}  page {chunk.page_start}  {chunk.chunk_id[-3:]}  {chunk.heading[:60]}{mark}")
    ranks = report["needle_ranks"]
    if not ranks:
        print(f"\nNo chunk contains {args.needle!r}: wrong needle, or the text is split across chunks.")
    elif min(ranks) <= len(report["top"]):
        print(f"\nRETRIEVAL OK: a chunk with the needle is in the top {len(report['top'])} (best rank #{min(ranks)}).")
    else:
        print(f"\nRETRIEVAL MISS: chunks with the needle rank {ranks[:5]} (outside the top {len(report['top'])}).")

    if args.ask:
        provider = build_provider()
        prompt = _prompt(args.kind, report["prompt_chunks"])
        print("\nRAW MODEL ANSWER")
        print(provider.generate_json(SYSTEM, prompt, FORMS[args.kind]))


if __name__ == "__main__":
    main()