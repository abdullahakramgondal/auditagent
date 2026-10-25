"""Check the empty-answer safety net (hint_fires) on every contract, without any model call.

For every contract and clause type it counts the chunks that make the hint fire:
  MISS RISK    the contract has the rule but no chunk fires: an empty model answer would stay silent
  FALSE ALARM  the contract has no such rule but a chunk fires: an empty model answer would raise a needless review
It looks at all chunks of the contract, while Agent 1 only checks the chunks it showed the model.

Run:  python -m eval.hint_check
"""

import json
import tempfile
from pathlib import Path

from auditagent.agents.legal_extractor import KINDS, hint_fires
from auditagent.ingestion.chunker import chunk_document
from auditagent.ingestion.pdf_parser import parse_pdf
from data.generator.build_case import build_case

ROOT = Path(__file__).resolve().parents[1]
TIER_B_DIR = ROOT / "data" / "tier_b"


def contracts(tmp: str):
    """(name, spec, contract PDF) for every Tier A and every written Tier B contract."""
    for spec_path in sorted((ROOT / "data" / "specs").glob("*.json")):
        yield spec_path.stem, json.loads(spec_path.read_text()), build_case(spec_path, tmp) / "contract.pdf"
    for spec_path in sorted((TIER_B_DIR / "specs").glob("*.json")):
        pdf = TIER_B_DIR / "pdf" / f"{spec_path.stem}.pdf"
        if pdf.exists():
            yield spec_path.stem, json.loads(spec_path.read_text()), pdf


def main() -> None:
    with_rule = dict.fromkeys(KINDS, 0)
    without_rule = dict.fromkeys(KINDS, 0)
    miss_risk = {kind: [] for kind in KINDS}
    false_alarm = {kind: [] for kind in KINDS}

    with tempfile.TemporaryDirectory() as tmp:
        for name, spec, pdf in contracts(tmp):
            chunks = chunk_document(parse_pdf(pdf))
            present = {rule["clause_type"] for rule in spec["rules"]}
            for kind in KINDS:
                firing = sum(hint_fires(kind, chunk.text) for chunk in chunks)
                if kind in present:
                    with_rule[kind] += 1
                    if firing == 0:
                        miss_risk[kind].append(name)
                else:
                    without_rule[kind] += 1
                    if firing:
                        false_alarm[kind].append(f"{name} ({firing})")

    print(f"{'clause':16} {'with rule':>9} {'miss risk':>9} {'without':>8} {'false alarm':>11}")
    for kind in KINDS:
        print(f"{kind:16} {with_rule[kind]:>9} {len(miss_risk[kind]):>9} "
              f"{without_rule[kind]:>8} {len(false_alarm[kind]):>11}")
    for kind in KINDS:
        if miss_risk[kind]:
            print(f"\nMISS RISK  {kind}: {', '.join(miss_risk[kind])}")
        if false_alarm[kind]:
            print(f"FALSE ALARM {kind}: {', '.join(false_alarm[kind])}")


if __name__ == "__main__":
    main()