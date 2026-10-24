"""Find out why a rule was missed: was the right clause retrieved, and what does the model answer?

Run:  python -m eval.diagnose tb_04 unit_price --needle "275,000"            (retrieval only, no model call)
      python -m eval.diagnose tb_04 unit_price --needle "275,000" --ask      (also one model call, raw answer)
--needle is any text that appears in the clause the rule should come from.
It shows exactly the chunks Agent 1 sends to the model (same retrieve() function), in prompt order.
Tier B contracts only (data/tier_b/pdf). Sends clause text to the LLM when --ask is used.
"""

import argparse
from pathlib import Path

from auditagent.agents.legal_extractor import FORMS, RETRIEVAL_QUERIES, SYSTEM, TOP_K, _prompt, retrieve
from auditagent.ingestion.chunker import chunk_document
from auditagent.ingestion.embedder import Embedder, SentenceTransformerEmbedder
from auditagent.ingestion.pdf_parser import normalize_for_match, parse_pdf
from auditagent.ingestion.vectorstore import ContractIndex
from auditagent.llm.factory import build_provider

ROOT = Path(__file__).resolve().parents[1]


def retrieval_report(doc, kind: str, needle: str, embedder: Embedder, top_k: int = TOP_K) -> dict:
    """The chunks sent to the model for this clause type, and where the chunks holding `needle` are.

    needle_ranks: positions (1 = first in the prompt) of sent chunks that hold the needle.
    outside_ranks: ranks for the first query of chunks that hold the needle but were NOT sent.
    """
    chunks = chunk_document(doc)
    index = ContractIndex(embedder, chunks, doc_label=doc.sha256[:12])
    try:
        shown = retrieve(index, kind, top_k)
        ranking = index.search(RETRIEVAL_QUERIES[kind][0], k=len(chunks))
    finally:
        index.close()
    wanted = normalize_for_match(needle).lower()

    def holds(chunk) -> bool:
        return wanted in normalize_for_match(chunk.text).lower()

    rows = [(position, chunk, holds(chunk)) for position, chunk in enumerate(shown, start=1)]
    sent = {chunk.chunk_id for chunk in shown}
    return {
        "chunk_count": len(chunks),
        "top": rows,
        "needle_ranks": [position for position, _, found in rows if found],
        "outside_ranks": [
            rank for rank, hit in enumerate(ranking, start=1) if holds(hit.chunk) and hit.chunk.chunk_id not in sent
        ],
        "prompt_chunks": shown,
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

    print(f"{args.case_id} / {args.kind}: {report['chunk_count']} chunks. Queries:")
    for query in RETRIEVAL_QUERIES[args.kind]:
        print(f"   {query!r}")
    print(f"\nSENT TO THE MODEL ({len(report['top'])} chunks, in prompt order)")
    for position, chunk, found in report["top"]:
        mark = "   <== contains the needle" if found else ""
        print(f"  #{position}  page {chunk.page_start}  {chunk.chunk_id[-3:]}  {chunk.heading[:60]}{mark}")
    if report["needle_ranks"]:
        print(f"\nRETRIEVAL OK: a chunk with the needle is sent (best position #{min(report['needle_ranks'])}).")
    elif report["outside_ranks"]:
        print(
            f"\nRETRIEVAL MISS: chunks with the needle rank {report['outside_ranks'][:5]} "
            "for the first query and were not sent."
        )
    else:
        print(f"\nNo chunk contains {args.needle!r}: wrong needle, or the text is split across chunks.")

    if args.ask:
        provider = build_provider()
        prompt = _prompt(args.kind, report["prompt_chunks"])
        print("\nRAW MODEL ANSWER")
        print(provider.generate_json(SYSTEM, prompt, FORMS[args.kind]))


if __name__ == "__main__":
    main()