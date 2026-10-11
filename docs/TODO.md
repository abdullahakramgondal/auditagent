# Project tracker

## Deferred items (open, must not be skipped)

| # | Item | Why deferred | Do it in |
|---|------|--------------|----------|
| 1 | AuditResult: validator that total_difference == billed_total - correct_payable, and that the sum of finding differences == total_difference | Totals will be computed by code in the rule engine | Week 4, Day 22 |
| 2 | Invoice integrity checks: line_total == quantity x unit_price, and total_amount == sum(line_totals) + sum(adjustments). Produce a finding or NEEDS_REVIEW, never a schema error | An invoice that is wrong is a finding, not a crash | Week 3, Day 17 |
| 3 | Source grounding check: quote must exist in parsed contract text, page taken from parser, numbers in the rule must appear in the quote | Needs real Agent 1 output | Week 2, Day 11 |
| 5 | ADR note: "Schemas validate shape only; code computes totals" | Write once the rule engine exists | Week 4 |
| 7 | Add `ollama` to requirements.in, install Ollama, check laptop RAM/GPU | Needed only for Week 2 comparison | Week 2, Day 8 |
| 8 | Before making the repo public: scan for API keys and secrets | Keys cannot be taken back once public | Before going public |
| 9 | Split requirements-dev.txt, add real ci.yml, delete unused skeleton files | Not needed yet | Week 6 |
| 13 | Week 4 rule engine must be written independently of ground_truth.py (never import or copy it) | Otherwise both can share the same mistake and evaluation becomes meaningless | Week 4 |
| 14 | Realistic evaluation tiers: Tier B (8-10 LLM-written long contracts from specs, hand-verified, written by at least 2 different AIs plus 1-2 by hand), Tier C (2-3 messy documents with tables, headers, scattered clauses) | Needs a working Agent 1 first | Week 2 Day 9-10 and Week 3 |
| 15 | Agent 3 must read vendor deductions from invoice adjustments, never from the spec | vendor_applied exists only in the answer key | Week 4 |
| 16 | Contract boilerplate is only 6 repeated generic clauses, so 20-page contracts look repetitive. Add more varied filler text and clause wording | Needs time; not blocking | Day 5 or later |
| 17 | Agent 2 must handle three date formats (25 October 2026, 25-Oct-2026, 25/10/2026, all day first), label synonyms (Invoice No / Bill No / Invoice #) and normalize dates to ISO | Needs Agent 2 | Week 3 |

## Completed items

| # | Item | Result |
|---|------|--------|
| 4 | Should sum of findings match total_difference? | Yes. Discount and penalty are computed separately on the same base, and total_difference = sum of finding amounts (see scope.md) |
| 6 | scope.md: whole-unit quantities only | Done |
| 10 | PO and invoice layout variants | Done: three layouts (doc_variant 1 to 3) |
| 11 | Extend ground_truth.py to all four clause types | Done |
| 12 | Dataset sanity tests for all specs | Done in test_spec_generator.py |

## Checkpoints
- Day 12: Agent 1 accuracy number measured
- Day 25: end-to-end pipeline runs, even if rough
- Week 6: final evaluation, deploy, demo video

## Done so far
- Day 1: scope.md and example_case.md
- Day 2: schemas (contract, invoice/PO, audit) with passing tests
- Day 3: clause templates, contract/PO/invoice PDFs, expected.json builder, learning notes
- Day 4: ground truth for all four clause types, spec generator (30 cases, 10 categories), invoice adjustments, three PO/invoice layouts (61 tests passing)