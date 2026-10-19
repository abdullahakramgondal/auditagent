"""List where Agent 1's quote does not contain the whole gold clause text (values were still right).

Run:  python -m eval.quote_gaps            (uses the saved results of the default model)
"""

import json
import sys
from pathlib import Path

from auditagent.ingestion.pdf_parser import normalize_for_match

ROOT = Path(__file__).resolve().parents[1]


def main(model: str = "gemini-3.1-flash-lite") -> None:
    shown = 0
    for path in sorted((ROOT / "eval" / "results" / f"agent1_{model}").glob("*.json")):
        saved = json.loads(path.read_text())
        for rule in saved["result"]["contract"]["rules"]:
            gold = saved["gold_sources"].get(rule["clause_type"])
            if gold and normalize_for_match(gold["text"]) not in normalize_for_match(rule["source"]["text"]):
                shown += 1
                print(f"{path.stem}  {rule['clause_type']}")
                print("   gold :", gold["text"])
                print("   quote:", rule["source"]["text"])
    print(f"\n{shown} rule(s) where the quote is shorter than or different from the gold clause")


if __name__ == "__main__":
    main(*sys.argv[1:2])