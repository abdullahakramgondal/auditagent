# Project tracker

## Deferred items (decided later, must not be skipped)

| # | Item | Why deferred | Do it in |
|---|------|--------------|----------|
| 1 | AuditResult: validator that total_difference == billed_total - correct_payable | Totals will be computed by code in the rule engine | Week 4, Day 22 |
| 2 | Invoice integrity checks: line_total == quantity x unit_price, total_amount == sum of line totals. Produce a finding or NEEDS_REVIEW, never a schema error | An invoice that is wrong is a finding, not a crash | Week 3, Day 17 |
| 3 | Source grounding check: quote must exist in parsed contract text, page taken from parser, numbers in the rule must appear in the quote | Needs real Agent 1 output | Week 2, Day 11 |
| 4 | Decide whether sum of findings should match total_difference (findings can interact) | Depends on rule engine design | Week 4, Day 22 |
| 5 | ADR note: "Schemas validate shape only; code computes totals" | Write once the rule engine exists | Week 4 |
| 6 | scope.md: add "quantity is whole units only" under out of scope | One line | Day 3 |
| 7 | Add `ollama` to requirements.in, install Ollama, check laptop RAM/GPU | Needed only for Week 2 comparison | Week 2, Day 8 |
| 8 | Before making the repo public: scan for API keys and secrets | Keys cannot be taken back once public | Before going public |
| 9 | Split requirements-dev.txt, add real ci.yml, delete unused skeleton files | Not needed yet | Week 6 |
|10	| PO and invoice need 2 to 3 layout variants (right now every document looks the same, which makes Agent 2 evaluation too easy)	|Day 4|
|11	|Extend ground_truth.py to volume discount, unit price, payment terms|	Day 4|

## Checkpoints
- Day 12: Agent 1 accuracy number measured
- Day 25: end-to-end pipeline runs, even if rough
- Week 6: final evaluation, deploy, demo video

## Done so far
- Day 1: scope.md and example_case.md
- Day 2: schemas (contract, invoice/PO, audit) with 8 passing tests
- Day 3: clause templates (3 wording variants, decoy clauses)
- Day 3: clause templates, contract/PO/invoice PDFs, expected.json builder