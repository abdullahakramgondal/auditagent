# Project tracker

## Open items (must not be skipped)

| # | Item | When |
|---|------|------|
| 1 | AuditResult validator: total_difference == billed_total - correct_payable, and == sum of finding differences | Week 4 |
| 2 | Invoice integrity: line_total == qty x unit_price; total == sum(lines) + sum(adjustments). A wrong invoice is a finding or NEEDS_REVIEW, never a schema error | Week 3 |
| 3 | Grounding, still open: fuzzy near-verbatim quotes (rapidfuzz), number words, quotes spanning two chunks. Done already: quote must exist, numbers/dates in the right role, page from the parser. If partial quotes (item 41) keep causing refusals, the fallback is to check the values against the whole clause (chunk) instead of the quote; that weakens grounding, so only with evidence | Day 13+ |
| 5 | ADR: "schemas validate shape only; code computes totals" | Week 4 |
| 7 | Ollama: test ONE small model (1-3B) as an experiment with other apps closed; measure accuracy, time, memory. Laptop: 8 GB RAM, no dedicated GPU, so 7B+ is not realistic. Needs llm/base.py, factory.py, gemini.py and config.py to add a provider the same way | Day 13 |
| 8 | Scan for API keys and secrets before the repo is made public | Before public |
| 9 | Split requirements-dev, real ci.yml, delete unused skeleton files and folders | Week 6 |
| 13 | Rule engine written independently of ground_truth.py (never import or copy it) | Week 4 |
| 14 | Tier C: 2-3 messy documents (tables, headers, scattered clauses). Tier B tb_01 to tb_08 are written and checked | Day 13, Week 3 |
| 15 | Agent 3 reads vendor deductions from invoice adjustments, never from the spec | Week 4 |
| 16 | Contract boilerplate repeats; add varied filler text | later |
| 17 | Agent 2: three date formats, label synonyms (Invoice No / Bill No / Invoice #), normalise dates to ISO | Week 3 |
| 18 | Layout 2 invoices (two-column header) may mix reading order; use word coordinates if Agent 2 fails | Week 3 |
| 19 | OCR fallback for scanned PDFs (optional, out of v1 scope) | Week 6 |
| 20 | Retrieval can return decoy clauses in the top-k; Agent 1 must pick the real rule. Up to 11 chunks now reach the model for late_penalty (TOP_K 8 + 3 extra): watch this on Tier B/C | Tier B/C |
| 21 | Chunker assumes numbered headings; tb_01 to tb_04 worked (about 133 of 135 chunks with headings); other styles untested | Tier B/C |
| 22 | Hybrid retrieval (keywords + embeddings) only if the eval shows a need | later |
| 23 | Retrieval eval is easy on synthetic data. Re-run eval.retrieval_eval with the new retrieve() (it has a new `sent` column) and check Tier B with eval.diagnose. Tier B showed two retrieval misses so far: tb_04 unit_price (rank 8 with the old query) and the tb_04 date clause (rank 14 for the penalty query) | Day 13 |
| 24 | unit_price recall@1 is 0.6 (top-3 is 1.0); low priority | later |
| 25 | Docker on 8 GB RAM: limit WSL memory, close other apps | Week 6 |
| 26 | Docstring pass on src/ (many public functions have none); enable ruff pydocstyle for src/ only. Still without docstrings: the form classes in legal_forms.py (add them whenever that file is touched) | Week 6 |
| 27 | Numbers written only as words ("thirty days") are refused by grounding; Tier B so far writes "forty (40)", which works | Tier B |
| 28 | Agent 1 issues (refused rules, unusable output, "needs review" hints) must become review reasons in Agent 3: NEEDS_REVIEW, never a silent COMPLIANT | Week 4 |
| 30 | Free-tier rate limits and pacing; always save the exact model name in results | ongoing |
| 31 | Run `ruff check .` and `ruff format .` (never run yet) and fix findings. Do it in its own commit | Day 13 |
| 32 | Trim requirements to what we import (pandas, scikit-learn, rapidfuzz unused so far) | Week 6 |
| 33 | ADR: why ChromaDB for a per-document index (proposal choice, isolated behind ContractIndex; numpy would do) | Week 2 |
| 34 | Structured logging with a run id per audit; create the embedder once per process | Week 4-5 |
| 35 | Complexity audit: for every module ask "what breaks if I delete this?"; remove dead code and unused skeleton folders; count lines per folder; delete one-off scripts (quote_gaps.py, show_around.py) when done | End of Week 3, Week 6 |
| 36 | Decimal display: Gemini floats give '12.0' for 12; normalise in reports | Week 5 |
| 37 | Quotes may include the clause heading; compare quotes by containment, never equality | always |
| 38 | Eval timing is not comparable between runs: with 4 model calls each, contracts took anywhere from 6 s to 77 s with the same code, and in the fast run each call took 1 to 3 s, so the waiting is the provider (rate limits), not our code. Record retries or wait time per call to be sure | Day 13 |
| 40 | Do not tune prompts on synthetic Tier A any more; use Tier B and C | always |
| 41 | Quote accuracy 0.93 (Tier A, unchanged after the Day 12 prompt change): on 4 two-sentence unit_price clauses the model quotes only the sentence with the price (values right). Accepted for v1. The late_penalty task now asks for every sentence that states a value (tb_06); volume_discount, payment_terms and unit_price tasks do not. If partial quotes make a rule refused there too, give them the same instruction | Tier B/C |
| 42 | Prompt leakage: TASKS names the same decoys the generator plants (liability caps, late payment charges). Re-test with decoys the prompt does not mention | Tier B/C |
| 43 | Every regex that reads real text needs word boundaries and a required digit; tests need realistic text ("Vendors,") | always |
| 44 | Never copy a regex: patterns live in grounding.py (PERCENT_RE, DAYS_RE, UNITS_RE) and are imported | always |
| 46 | tb_01: Gemini returned cap_percent 8 for a flat 8% penalty (no cap in spec). It did not repeat in the last four Tier B runs (8 contracts), but nothing was changed for it, so it is model variance. Decide after the next fresh contracts: say in the form that cap_percent is only for per_day_percent, or normalise | Day 13+ |
| 47 | Grounding blind spot: one number used in two roles (percent 8 and cap 8) passes. Idea: require it twice in the quote | Day 13+ |
| 52 | Review hints were fixed from the false alarms seen so far (tb_02, tb_03, gen_007, gen_018, gen_022, gen_023, gen_024). Tier A (31) and Tier B (8) now give 0 review issues. Still to check on fresh contracts (item 58): false alarms and missed alarms | Day 13+ |
| 55 | The defined-term link (item 48 fix) handles only date terms ending in Deadline, Date or Day, written as (the "X") or "X" means. A date written in the same clause without a defined term works only if the quote holds that sentence (tb_06). A date in a table, a term like "Delivery Period", or no date near the penalty at all are untested: fresh contracts and Tier C will show | Tier B/C |
| 56 | gen_011: in one Tier A run the model wrote item_name "Leased Line 100 Mbps" although its own quote says "Leased Line 100 Mbps (annual)"; in the next run it was right, so it is model variance. Grounding accepts the short name (it is inside the quote). Agent 2 and Agent 3 must match items by normalised containment, never by equality | Week 3 |
| 57 | Eval cache can mix code versions: after a laptop sleep interrupted a run, the second start reused results from the old code. Save the git commit in every cached result and warn when a reused result comes from another commit. Until then: set the laptop to never sleep during runs and delete the cache folder before a full re-run | Day 13 |
| 58 | No untouched test set left: tb_05 to tb_08 were looked at while fixing tb_06 (Day 12), and tb_01 to tb_04 earlier. Write tb_09 to tb_12 (prompts via make_prompts.py, alternate Claude and ChatGPT, check each with check_contract, never edit a contract after seeing Agent 1's result) or use Tier C, and run Agent 1 on them ONCE without tuning | Day 13, Week 3 |

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
| 14 (part) | Tier B tb_05 to tb_08 | Done: written, checked with check_contract, run through Agent 1 |
| 48 | Defined terms: tb_04 penalty clause says "after the Delivery Deadline", date in clause 5.1 | Done: the date clause ranked 14 for the penalty query, so late_penalty now uses a second query (retrieve() adds 3 chunks; clause 5.1 arrives at position 9 of 11). The form has deadline_quote and the rule keeps deadline_source (page and text where the date is written). The date counts only if that quote exists in the contract and defines a date term, for example (the "Delivery Deadline"), that the penalty quote uses, so decoy clauses cannot borrow a date. Limits: item 55 |
| 49 | SILENT MISS tb_04 unit_price (clause 7.1, page 4) | Done: eval/diagnose.py showed the clause at rank 8 while TOP_K was 5, so the model never saw it. Fixed by rewording the unit_price retrieval query and TOP_K 5 to 8. Safety net added: keywords found but no rule extracted = "needs review" issue, never silence |
| 50 | Save raw model answers per call in the eval cache | Done: every cached result has raw_answers (task, chunk ids sent, seconds, raw text) |
| 51 | Measure Agent 1 on Tier B | Done: 8 contracts, 20 rules: 20 correct, 0 wrong, 0 refused, 0 silent, 0 issues. History on tb_01 to tb_04: Day 10 recall 0.73, Day 11 recall 0.91, Day 12 1.00. See item 58 for why this is not a clean test |
| 53 | Tier A re-run with the new code | Done: 31 contracts, 58 rules: 58 correct, 0 wrong, 0 refused, 0 silent, 0 spurious, 0 review issues; field 1.00, page 1.00, quote 0.93 |
| 54 | HINTS untested, payment_terms hint missed "payable 30 calendar days after", false alarms | Done: hint_fires() in legal_extractor.py with its own tests (test_retrieval_and_hints.py). The late_penalty hint skips delayed or late PAYMENT ("late payment", "delays payment", "delay in payment"). The payment_terms hint needs the words invoice and a payment word (pay, paid, settle, due) plus DAYS_RE (imported from grounding.py) |
| 59 | tb_06 late_penalty refused: values right, quote held only the penalty sentence | Done: clause 7.3 spreads the date, the grace period and the penalty over three sentences with no defined term. The late_penalty task now tells the model to quote every sentence that states a value of the rule, together and in order. Two tests added (whole clause accepted, penalty sentence alone refused). Tier B 20/20 after the change |

## Checkpoints
- Day 12: Agent 1 numbers on Tier A and Tier B: done (see Done so far). The local small-model experiment moved to Day 13
- Day 13: buffer day: ruff, Ollama experiment, items 23, 38, 57, 58
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
- Day 12: Agent 1 evaluation finished. A date written in another clause now works (second retrieval query for late_penalty, deadline_quote in the form, deadline_source on the rule, defined-term link check in grounding.py). Review hints tightened and tested (hint_fires); diagnose and retrieval_eval share retrieve() with Agent 1; the eval cache keeps raw model answers with seconds per call. tb_05 to tb_08 written and checked. tb_06 (date, grace and penalty in three sentences of one clause, quote held one) fixed by asking for every value sentence in the late_penalty task. Final numbers on the same code: Tier A (31 contracts, 58 rules): 58 correct, 0 wrong, 0 refused, 0 silent, 0 spurious, 0 review issues; field 1.00, page 1.00, quote 0.93. Tier B (8 contracts, 20 rules): 20 correct, 0 issues; field 1.00. 186 tests. Moved to Day 13: Ollama experiment, ruff