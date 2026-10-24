# Project tracker

## Open items (must not be skipped)

| # | Item | When |
|---|------|------|
| 1 | AuditResult validator: total_difference == billed_total - correct_payable, and == sum of finding differences | Week 4 |
| 2 | Invoice integrity: line_total == qty x unit_price; total == sum(lines) + sum(adjustments). A wrong invoice is a finding or NEEDS_REVIEW, never a schema error | Week 3 |
| 3 | Grounding, still open: fuzzy near-verbatim quotes (rapidfuzz), number words, quotes spanning two chunks. Done already: quote must exist, numbers/dates in the right role, page from the parser | Day 12+ |
| 5 | ADR: "schemas validate shape only; code computes totals" | Week 4 |
| 7 | Ollama: test ONE small model (1-3B) as an experiment with other apps closed; measure accuracy, time, memory. Laptop: 8 GB RAM, no dedicated GPU, so 7B+ is not realistic | Day 12 |
| 8 | Scan for API keys and secrets before the repo is made public | Before public |
| 9 | Split requirements-dev, real ci.yml, delete unused skeleton files and folders | Week 6 |
| 13 | Rule engine written independently of ground_truth.py (never import or copy it) | Week 4 |
| 14 | Tier B: tb_05 to tb_08 still to write and check (alternate Claude and ChatGPT). Tier C: 2-3 messy documents (tables, headers, scattered clauses) | Day 12, Week 3 |
| 15 | Agent 3 reads vendor deductions from invoice adjustments, never from the spec | Week 4 |
| 16 | Contract boilerplate repeats; add varied filler text | later |
| 17 | Agent 2: three date formats, label synonyms (Invoice No / Bill No / Invoice #), normalise dates to ISO | Week 3 |
| 18 | Layout 2 invoices (two-column header) may mix reading order; use word coordinates if Agent 2 fails | Week 3 |
| 19 | OCR fallback for scanned PDFs (optional, out of v1 scope) | Week 6 |
| 20 | Retrieval can return decoy clauses in the top-k; Agent 1 must pick the real rule. Up to 11 chunks now reach the model for late_penalty (TOP_K 8 + 3 extra): watch this on Tier B/C | Tier B/C |
| 21 | Chunker assumes numbered headings; tb_01 to tb_04 worked (about 133 of 135 chunks with headings); other styles untested | Tier B/C |
| 22 | Hybrid retrieval (keywords + embeddings) only if the eval shows a need | later |
| 23 | Retrieval eval is easy on synthetic data. Re-run eval.retrieval_eval with the new retrieve() (it has a new `sent` column) and check Tier B with eval.diagnose. Tier B showed two retrieval misses so far: tb_04 unit_price (rank 8 with the old query) and the tb_04 date clause (rank 14 for the penalty query) | Day 12 |
| 24 | unit_price recall@1 is 0.6 (top-3 is 1.0); low priority | later |
| 25 | Docker on 8 GB RAM: limit WSL memory, close other apps | Week 6 |
| 26 | Docstring pass on src/ (many public functions have none); enable ruff pydocstyle for src/ only. No docstrings yet: LegalExtractor and its helpers in legal_extractor.py, the form classes in legal_forms.py (add them whenever those files are touched) | Week 6 |
| 27 | Numbers written only as words ("thirty days") are refused by grounding; Tier B so far writes "forty (40)", which works | Tier B |
| 28 | Agent 1 issues (refused rules, unusable output, "needs review" hints) must become review reasons in Agent 3: NEEDS_REVIEW, never a silent COMPLIANT | Week 4 |
| 30 | Free-tier rate limits and pacing; always save the exact model name in results | ongoing |
| 31 | Run `ruff check .` and `ruff format .` (never run yet) and fix findings. Do it in its own commit | Day 12 |
| 32 | Trim requirements to what we import (pandas, scikit-learn, rapidfuzz unused so far) | Week 6 |
| 33 | ADR: why ChromaDB for a per-document index (proposal choice, isolated behind ContractIndex; numpy would do) | Week 2 |
| 34 | Structured logging with a run id per audit; create the embedder once per process | Week 4-5 |
| 35 | Complexity audit: for every module ask "what breaks if I delete this?"; remove dead code and unused skeleton folders; count lines per folder; delete one-off scripts (quote_gaps.py, show_around.py) when done | End of Week 3, Week 6 |
| 36 | Decimal display: Gemini floats give '12.0' for 12; normalise in reports | Week 5 |
| 37 | Quotes may include the clause heading; compare quotes by containment, never equality | always |
| 38 | Eval timing: record provider rate-limit retries. Tier B went from 6.8 s to 35.1 s per contract with the same 4 model calls after TOP_K 8 + extra chunks: find out whether it is retries or bigger prompts (about 20 minutes for Tier A at this speed) | Day 12 |
| 40 | Do not tune prompts on synthetic Tier A any more; use Tier B and C | always |
| 41 | Quote accuracy 0.93: on 4 two-sentence unit_price clauses the model quoted only the sentence with the price (values right). Accepted for v1. Re-check on Tier B for dropped exception sentences | Tier B |
| 42 | Prompt leakage: TASKS names the same decoys the generator plants (liability caps, late payment charges). Re-test with decoys the prompt does not mention | Tier B |
| 43 | Every regex that reads real text needs word boundaries and a required digit; tests need realistic text ("Vendors,") | always |
| 44 | Never copy a regex: patterns live in grounding.py (PERCENT_RE, DAYS_RE, UNITS_RE) and are imported | always |
| 46 | tb_01: Gemini returned cap_percent 8 for a flat 8% penalty (no cap in spec). It did not repeat in the last two Tier B runs (field accuracy 1.00), but nothing was changed for it, so it is model variance. Decide after all 8 contracts: say in the form that cap_percent is only for per_day_percent, or normalise | Day 12 |
| 47 | Grounding blind spot: one number used in two roles (percent 8 and cap 8) passes. Idea: require it twice in the quote | Day 12+ |
| 50 | Save raw model answers per call in the eval cache so failures can be diagnosed without new calls. Can be done inside CountingProvider in eval/agent1_eval.py, which already sees every raw answer. Do it BEFORE the Tier A --fresh run | Day 12 |
| 51 | Tier B after the Day 12 fixes (4 contracts, 11 rules): 11 correct, 0 wrong, 0 refused, 0 silent, 0 issues; recall 1.00, precision 1.00, field accuracy 1.00. Earlier: Day 10 8/1/1/1 (recall 0.73), Day 11 10/0/1/0 (recall 0.91). tb_01 to tb_04 are the contracts the fixes were made on, so this proves little: tb_05 to tb_08 are the untouched check, do not tune on them | Day 12 |
| 52 | Safety net false alarms: the two Tier B false alarms (tb_02 payment_terms, tb_03 late_penalty) are gone, but the new hint patterns were written from those two examples only. Still to measure: false alarms on Tier A correct_absent cases (item 53) and on tb_05 to tb_08 | Day 12 |
| 53 | Tier A saved results come from the old code (TOP_K 5, no safety net). Re-run with --fresh to confirm 58/58 still holds and to count "needs review" issues on cases that have no such rule. Do not tune on Tier A (item 40). Takes about 20 minutes | Day 12 |
| 55 | The defined-term link (item 48 fix) handles only date terms ending in Deadline, Date or Day, written as (the "X") or "X" means. A date in a table, a term like "Delivery Period", or no defined term at all are untested: tb_05 to tb_08 and Tier C will show | Tier B/C |

## Completed items

| # | Item | Result |
|---|------|--------|
| 4 | Should sum of findings match total_difference? | Yes. Discount and penalty are computed separately on the same base; total_difference = sum of finding amounts (see scope.md) |
| 6 | scope.md: whole-unit quantities only | Done |
| 10 | PO and invoice layout variants | Done: three layouts (doc_variant 1 to 3) |
| 11 | ground_truth.py for all four clause types | Done |
| 12 | Dataset sanity tests for all specs | Done in test_spec_generator.py |
| 29 | RETRIEVAL_QUERIES defined twice | Done: legal_extractor.py owns RETRIEVAL_QUERIES (a tuple of queries per clause type) and retrieve(); eval/diagnose.py and eval/retrieval_eval.py import them. retrieval_eval.py not re-run yet (item 23) |
| 39 | Hard categories on Tier A (unit_price, decoy, multi_breach) | Done: 58/58 on gemini-3.1-flash-lite |
| 48 | Defined terms: tb_04 penalty clause says "after the Delivery Deadline", date in clause 5.1 | Done: the date clause ranked 14 for the penalty query, so late_penalty now uses a second query (retrieve() adds 3 chunks; clause 5.1 arrives at position 9 of 11). The form has deadline_quote and the rule keeps deadline_source (page and text where the date is written). The date counts only if that quote exists in the contract and defines a date term, for example (the "Delivery Deadline"), that the penalty quote uses, so decoy clauses cannot borrow a date. tb_04 late_penalty is now correct. Limits: item 55 |
| 49 | SILENT MISS tb_04 unit_price (clause 7.1, page 4) | Done: eval/diagnose.py showed the clause at rank 8 while TOP_K was 5, so the model never saw it. Fixed by rewording the unit_price retrieval query and TOP_K 5 to 8. Safety net added: keywords found but no rule extracted = "needs review" issue, never silence |
| 54 | HINTS untested, payment_terms hint missed "payable 30 calendar days after" | Done: hint_fires() in legal_extractor.py with its own tests (test_retrieval_and_hints.py). The late_penalty hint ignores "late payment" charges; the payment_terms hint needs the word invoice plus DAYS_RE (imported from grounding.py). 180 tests passing |

## Checkpoints
- Day 12: Agent 1 numbers on Tier A and Tier B (all 8 contracts), and the local small-model experiment
- Day 25: end-to-end pipeline runs, even if rough
- Week 6: final evaluation, deploy, demo video, presentation

## Done so far
- Day 1: scope.md and example_case.md
- Day 2: schemas (contract, invoice/PO, audit) with passing tests
- Day 3: clause templates, contract/PO/invoice PDFs, expected.json builder, learning notes
- Day 4: ground truth for all four clause types, spec generator (30 cases, 10 categories), invoice adjustments, three PO/invoice layouts
- Day 5: PDF parser (page-wise text, hash, warnings, size and page limits), ParsedDocument schema
- Day 6: clause-aware chunker (header/footer removal), embedder interface (local MiniLM and offline hashing baseline), per-document in-memory ChromaDB index, retrieval eval. 58 clause/contract pairs: MiniLM recall@3 = 1.0 (hashing baseline 0.966). Decision: MiniLM, top-5 chunks to Agent 1
- Day 7: rest day
- Day 8: settings with SecretStr key, LLM provider interface with retries (Gemini, scripted fake for tests), smoke test on gemini-3.1-flash-lite (1.5 s), Agent 1 v1 (retrieval, LLM form, grounding checks, page from parser, issues list); first real run on gen_010: 3 rules, all matched the spec
- Day 9: Agent 1 evaluation harness (scoring, saved results, runner). Tier A, 31 contracts / 58 rules: 58 correct, 0 wrong, 0 refused, 0 silent, 0 spurious; field 1.00, page 1.00, quote 0.93; median 9.9 s, 4 model calls per contract. Conclusion: the test is too easy
- Day 10: Tier B started: 8 specs and prompts, tb_01 to tb_04 written by Claude/ChatGPT and checked with check_contract. Two real bugs found by it and fixed (rupee regex matching "Vendors,", units regex missing "forty (40) units"). Tier B (4 contracts, 11 rules): 8 correct, 1 wrong, 1 refused (hallucinated deadline caught by grounding), 1 silent miss. 162 tests passing
- Day 11: eval/diagnose.py (where does the needle rank, what does the model answer). It found the tb_04 unit_price silent miss: clause 7.1 was rank 8 and top-5 cut it off. Fixed: unit_price query reworded, TOP_K 8, HINTS safety net for empty answers. Tier B (4 contracts, 11 rules): 10 correct, 0 wrong, 1 refused (tb_04 deadline in a defined term), 0 silent; recall 0.91, precision 1.00, field accuracy 1.00. The safety net gave 2 false alarms. 163 tests passing
- Day 12 (in progress): date written in another clause now works: second retrieval query for late_penalty, deadline_quote in the form, deadline_source on the rule, defined-term link check in grounding.py. Review hints tightened (hint_fires with its own tests); diagnose and retrieval_eval now share retrieve() with Agent 1. 180 tests passing. Tier B (4 contracts, 11 rules): 11 correct, 0 wrong, 0 refused, 0 silent, 0 issues; recall 1.00, precision 1.00, field accuracy 1.00. Time per contract rose from 6.8 s to 35 s (item 38)