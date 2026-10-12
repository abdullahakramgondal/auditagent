"""Retrieval check on the synthetic dataset.

For every contract: is the clause that holds each rule among the top-k chunks when we
search with a plain-English description of the clause type?

Run:  python -m eval.retrieval_eval                      (semantic model, ~90 MB download once)
      python -m eval.retrieval_eval --embedder hashing   (offline word-matching baseline)
"""

import argparse
import json
import tempfile
from collections import defaultdict
from pathlib import Path

from auditagent.ingestion.chunker import chunk_document
from auditagent.ingestion.embedder import HashingEmbedder, SentenceTransformerEmbedder
from auditagent.ingestion.pdf_parser import normalize_for_match, parse_pdf
from auditagent.ingestion.vectorstore import ContractIndex
from data.generator.build_case import build_case

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "eval" / "results"

QUERIES = {
    "late_penalty": "penalty or deduction for late delivery of the goods",
    "volume_discount": "discount for ordering a large quantity of units",
    "payment_terms": "invoice payment due within a number of days",
    "unit_price": "agreed unit price per item that must not be exceeded",
}
DECOY_HEADINGS = ("Liability", "Late Payment")
KS = (1, 3, 5)


def evaluate(embedder, label: str) -> dict:
    found = defaultdict(lambda: {k: 0 for k in KS})
    total = defaultdict(int)
    decoy_top1 = defaultdict(int)
    misses = []

    with tempfile.TemporaryDirectory() as tmp:
        for spec_path in sorted((ROOT / "data" / "specs").glob("*.json")):
            out = build_case(spec_path, tmp)
            expected = json.loads((out / "expected.json").read_text())
            doc = parse_pdf(out / "contract.pdf")
            index = ContractIndex(embedder, chunk_document(doc), doc_label=doc.sha256[:12])

            for kind, source in expected["rule_sources"].items():
                gold = normalize_for_match(source["text"])
                hits = index.search(QUERIES[kind], k=max(KS))
                rank = next(
                    (i + 1 for i, h in enumerate(hits) if gold in normalize_for_match(h.chunk.text)),
                    None,
                )
                total[kind] += 1
                for k in KS:
                    if rank is not None and rank <= k:
                        found[kind][k] += 1
                if rank != 1 and any(d in hits[0].chunk.heading for d in DECOY_HEADINGS):
                    decoy_top1[kind] += 1
                if rank is None or rank > 3:
                    misses.append({"case": spec_path.stem, "clause": kind, "rank": rank})
            index.close()

    summary = {
        kind: {
            "n": total[kind],
            **{f"recall@{k}": round(found[kind][k] / total[kind], 3) for k in KS},
            "decoy_top1": decoy_top1[kind],
        }
        for kind in total
    }
    n_all = sum(total.values())
    summary["ALL"] = {
        "n": n_all,
        **{f"recall@{k}": round(sum(found[x][k] for x in total) / n_all, 3) for k in KS},
        "decoy_top1": sum(decoy_top1.values()),
    }
    return {"embedder": label, "summary": summary, "misses_below_top3": misses}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--embedder", choices=["minilm", "hashing"], default="minilm")
    args = parser.parse_args()
    embedder = SentenceTransformerEmbedder() if args.embedder == "minilm" else HashingEmbedder()

    result = evaluate(embedder, args.embedder)
    print(f"{'clause':16} {'n':>3} " + " ".join(f"recall@{k}" for k in KS) + "  decoy_top1")
    for kind, row in result["summary"].items():
        print(
            f"{kind:16} {row['n']:>3} "
            + " ".join(f"{row[f'recall@{k}']:>8}" for k in KS)
            + f"  {row['decoy_top1']:>5}"
        )
    print("misses below top-3:", len(result["misses_below_top3"]))

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / f"retrieval_{args.embedder}.json"
    out_path.write_text(json.dumps(result, indent=2))
    print("saved", out_path)


if __name__ == "__main__":
    main()