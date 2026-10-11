# Project tracker

## Deferred items (open, must not be skipped)

| # | Item | Why deferred | Do it in |
|---|------|--------------|----------|
| 1 | AuditResult: validator that total_difference == billed_total - correct_payable, and that the sum of finding differences == total_difference | Totals will be computed by code in the rule engine | Week 4, Day 22 |
| 2 | Invoice integrity checks: line_total == quantity x unit_price, total_amount == sum of line totals. Produce a finding or NEEDS_REVIEW, never a schema error | An invoice that is wrong is a finding, not a crash | Week 3, Day 17 |
| 3 | Source grounding check: quote must exist in parsed contract text, page taken from parser, numbers in the rule must appear in the quote | Needs real Agent 1 output | Week 2, Day 11 |
| 5 | ADR note: "Schemas validate shape only; code computes totals" | Write once the rule engine exists | Week 4 |
| 7 | Add `ollama` to requirements.in, install Ollama, check laptop RAM/GPU | Needed only for Week 2 comparison | Week 2, Day 8 |
| 8 | Before making the repo public: scan for API keys and secrets | Keys cannot be taken back once public | Before going public |
| 9 | Split requirements-dev.txt, add real ci.yml, delete unused skeleton files | Not needed yet | Week 6 |
| 10 | PO and invoice need 2 to 3 layout variants (right now every document looks the same, which makes Agent 2 evaluation too easy) | Needs the spec generator first | Day 4 |
| 12 | Dataset sanity tests: for all 30 cases, invoice total is consistent with vendor_applied, and billed_total - correct_payable == total_difference | Needs the 30 specs | Day 4 |
| 13 | Week 4 rule engine must be written independently of ground_truth.py (never import or copy it) | Otherwise both can share the same mistake and evaluation becomes meaningless | Week 4 |
| 14 | Realistic evaluation tiers: Tier B (8-10 LLM-written long contracts from specs, hand-verified, written by at least 2 different AIs plus 1-2 by hand), Tier C (2-3 messy docs with tables, headers, scattered clauses) | Needs a working Agent 1 first | Week 2, Day 9-10 and Week 3 |

## Completed items

| # | Item | Result |
|---|------|--------|
| 4 | Should sum of findings match total_difference? | Yes. Discount and penalty are computed separately on the same base, and total_difference = sum of finding amounts (see scope.md) |
| 6 | scope.md: whole-unit quantities only | Done |
| 11 | Extend ground_truth.py to all four clause types | Done, 41 tests passing |

## Checkpoints
- Day 12: Agent 1 accuracy number measured
- Day 25: end-to-end pipeline runs, even if rough
- Week 6: final evaluation, deploy, demo video

## Done so far
- Day 1: scope.md and example_case.md
- Day 2: schemas (contract, invoice/PO, audit) with passing tests
- Day 3: clause templates, contract/PO/invoice PDFs, expected.json builder, learning notes
- Day 4, step 1: ground truth for all four clause types (41 tests passing)