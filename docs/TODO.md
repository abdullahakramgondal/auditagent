# Project tracker

## Open items (must not be skipped)

| # | Item | When |
|---|------|------|
| 1 | AuditResult validator: total_difference == billed_total - correct_payable, and == sum of finding differences | Week 4 |
| 2 | Invoice integrity: line_total == qty x unit_price; total == sum(lines) + sum(adjustments). A wrong invoice is a finding or NEEDS_REVIEW, never a schema error | Week 3 |
| 3 | Grounding, still open: fuzzy near-verbatim quotes (rapidfuzz), number words, quotes spanning two chunks. Done already: quote must exist and be one continuous passage, numbers/dates in the right role, page from the parser. If partial quotes (item 41) keep causing refusals, the fallback is to check the values against the whole clause (chunk) instead of the quote; that weakens grounding, so only with evidence | Day 15+ |
| 5 | ADR: "schemas validate shape only; code computes totals" | Week 4 |
| 8 | Scan for API keys and secrets before the repo is made public | Before public |
| 9 | Split requirements-dev, real ci.yml (run `ruff check .`, `ruff format --check .` and `pytest -q`), delete unused skeleton files and folders | Week 6 |
| 13 | Rule engine written independently of ground_truth.py (never import or copy it) | Week 4 |
| 14 | Tier C: 2-3 messy documents (tables, headers, scattered clauses). Tier B tb_01 to tb_12 are written and checked | Day 15, Week 3 |
| 15 | Agent 3 reads vendor deductions from invoice adjustments, never from the spec | Week 4 |
| 16 | Contract boilerplate repeats; add varied filler text | later |
| 17 | Agent 2: three date formats, label synonyms (Invoice No / Bill No / Invoice #), normalise dates to ISO | Week 3 |
| 18 | Layout 2 invoices (two-column header) may mix reading order; use word coordinates if Agent 2 fails | Week 3 |
| 19 | OCR fallback for scanned PDFs (optional, out of v1 scope) | Week 6 |
| 20 | Retrieval can return decoy clauses in the top-k; Agent 1 must pick the real rule. Up to 11 chunks now reach the model for late_penalty (TOP_K 8 + 3 extra). tb_10 and tb_11 had decoys the prompt does not name (an early-settlement reduction, a support service credit) and Agent 1 ignored them | Tier B/C |
| 21 | Chunker assumes numbered headings: tb_01 to tb_04 about 133 of 135 chunks with headings, tb_09 to tb_12 134/135, 140/141, 93/95, 143/144, so numbered styles work; other styles untested | Tier C |
| 22 | Hybrid retrieval (keywords + embeddings) only if the eval shows a need | later |
| 23 | Re-run `python -m eval.retrieval_eval` with the new retrieve() (it has a new `sent` column) and check each new contract of item 58 with eval.diagnose. Tier B showed two retrieval misses so far: tb_04 unit_price (rank 8 with the old query) and the tb_04 date clause (rank 14 for the penalty query) | Day 15 |
| 24 | unit_price recall@1 is 0.6 (top-3 is 1.0); low priority | later |
| 25 | Docker on 8 GB RAM: limit WSL memory, close other apps | Week 6 |
| 26 | Docstring pass on src/ (many public functions have none); enable ruff pydocstyle for src/ only. Still without docstrings: the form classes in legal_forms.py (add them whenever that file is touched) | Week 6 |
| 27 | Numbers written only as words ("thirty days") are refused by grounding; Tier B so far writes "forty (40)", which works | Tier B |
| 28 | Agent 1 issues (refused rules, unusable output, "needs review" hints) must become review reasons in Agent 3: NEEDS_REVIEW, never a silent COMPLIANT. Add one line about it to scope.md then | Week 4 |
| 30 | Free-tier rate limits and pacing; always save the exact model name in results | ongoing |
| 32 | Trim requirements to what we import (pandas, scikit-learn, rapidfuzz unused so far; httpx is now used by llm/ollama.py) | Week 6 |
| 33 | ADR: why ChromaDB for a per-document index (proposal choice, isolated behind ContractIndex; numpy would do) | Week 2 |
| 34 | Structured logging with a run id per audit; create the embedder once per process | Week 4-5 |
| 35 | Complexity audit: for every module ask "what breaks if I delete this?"; remove dead code and unused skeleton folders; count lines per folder; delete one-off scripts (quote_gaps.py, show_around.py) when done | End of Week 3, Week 6 |
| 36 | Decimal display: Gemini floats give '12.0' for 12; normalise in reports | Week 5 |
| 37 | Quotes may include the clause heading; compare quotes by containment, never equality | always |
| 38 | Eval timing is not comparable between runs: the same code needed 6 s to 243 s per contract, and in the last Tier A run single calls took up to 90 s (a whole contract 169 s) while the fast runs took 1 to 3 s per call, so the waiting is the provider (rate limits), not our code. llm/gemini.py waits 2, 4, 8, 16 s (up to 60 s) between up to 5 tries on a 429 or 503 and prints nothing while it waits, which looks like a frozen run. Print the retries so a wait is visible | Day 15 |
| 40 | Do not tune prompts on synthetic Tier A any more; use Tier B and C | always |
| 41 | Quote accuracy 0.93 (Tier A): on 4 two-sentence unit_price clauses the model quotes only the sentence with the price (values right). Accepted for v1. The late_penalty task asks for every sentence that states the percentage, the cap or the grace period; volume_discount, payment_terms and unit_price tasks do not. If partial quotes make a rule refused there too, give them the same instruction | Tier B/C |
| 42 | Prompt leakage: TASKS names the same decoys the generator plants (liability caps, late payment charges). Partial evidence that it is harmless: the new decoys of tb_10 and tb_11 are not named in TASKS and were ignored. Re-test on the next batch | Tier B/C |
| 43 | Every regex that reads real text needs word boundaries and a required digit; tests need realistic text ("Vendors,") | always |
| 44 | Never copy a regex: patterns live in grounding.py (PERCENT_RE, DAYS_RE, UNITS_RE) and are imported | always |
| 46 | The model invents a cap_percent equal to the percentage for a FLAT penalty: tb_01 (Day 10 and 11) and tb_04 (twice on Day 14). That is a habit, not variance. Since Day 14 the cap check refuses it for review (item 65), which keeps it from passing but loses the rule. Decide: a flat_percent rule has no cap, so drop cap_percent when mode is flat_percent (the money maths does not change), or tell the form that cap_percent is only for per_day_percent. Note: a flat rule with a cap that differs from the percentage (for example the 12% of a liability clause) is not caught by the check | Day 15 |
| 52 | Review hints are measured by `python -m eval.hint_check` (no model call): on 43 contracts miss risk 0 and false alarm 0 for all four clause types. tb_09 to tb_12 were not used to write the hints, which is a real (small) test. Re-run on every new contract and fix only what a real contract shows | always |
| 55 | The defined-term link handles only date terms ending in Deadline, Date or Day, written as (the "X") or "X" means; it worked on tb_09 (curly quotes in the PDF). A date in the same clause works through deadline_quote (tb_06, tb_12). A date in a table, a term like "Delivery Period", or no date near the penalty at all are untested: fresh contracts and Tier C will show | Tier B/C |
| 56 | gen_011: in one Tier A run the model wrote item_name "Leased Line 100 Mbps" although its own quote says "Leased Line 100 Mbps (annual)"; in the next two runs it was right. Grounding accepts the short name (it is inside the quote). Agent 2 and Agent 3 must match items by normalised containment, never by equality | Week 3 |
| 57 | Eval cache can mix code versions or hide that nothing ran: after a laptop sleep the second start reused old results (Day 12), and on Day 14 a failed PowerShell command left the old Tier A cache in place, so "58/58" was an old result. Save a hash of legal_extractor.py, grounding.py and legal_forms.py in every cached result and refuse to reuse a result made with a different hash; print "REUSED (old code)" clearly. Until then: delete the cache folder with `Remove-Item -Recurse -Force` (PowerShell) and check that every contract says "done in" | Day 15 |
| 58 | New untouched batch: tb_09 to tb_12 were looked at while fixing (Day 14), so write tb_13 to tb_16 and run Agent 1 on them ONCE without tuning (prompts via make_prompts.py, alternate Claude and ChatGPT, check each with check_contract, freeze them in git BEFORE running Agent 1, never edit after). Ask for the hard cases again: dates in other clauses, wording without the usual keywords, contracts without some rule, decoys with numbers | Day 15 |
| 60 | Date format: the small local model wrote '20 November 2026' where the form asks YYYY-MM-DD; Gemini never did. A tolerant date parser in Agent 1 was NOT added on purpose (it would make the small model look better than it is). Agent 2 needs date normalisation anyway (item 17). If it is ever added to Agent 1, re-measure both providers | Week 3 |
| 61 | README ablation: write down the small-model result (qwen2.5:3b on this laptop, Tier B: 4 of 20 rules, 0 wrong rules passed, 94 s per contract on CPU) next to Gemini (20 of 20 then). The point: grounding and the safety net turn a weak model's failures into "needs review" | Week 6 |
| 62 | Never change prompts, grounding or retrieval because of a small local model's failures; Gemini stays the reference. Fix only what is also a weakness with Gemini (the tb_08 hint was one), then run `pytest -q` and `python -m eval.hint_check` | always |
| 66 | After ANY prompt, grounding or retrieval change run the whole regression set: `pytest -q`, `ruff check .`, `python -m eval.hint_check`, Tier B with --fresh (12 contracts) and Tier A from an emptied cache (31 contracts, about 10 to 40 minutes). On Day 14 one prompt fixed tb_09 and broke tb_06 and tb_12 within the hour; only the full Tier B run showed it | always |

## Completed items

| # | Item | Result |
|---|------|--------|
| 4 | Should sum of findings match total_difference? | Yes. Discount and penalty are computed separately on the same base; total_difference = sum of finding amounts (see scope.md) |
| 6 | scope.md: whole-unit quantities only | Done |
| 7 | Ollama: test ONE small model (1-3B) | Done: qwen2.5:3b through llm/ollama.py (settings OLLAMA_*, --provider flag in eval.agent1_eval and llm.smoke). Tier B, 8 contracts, 20 rules: 4 correct (recall 0.20, precision 1.00), 0 wrong, 0 spurious, 1 silent miss, 15 refused; 94 s per contract on CPU only; the model takes 2.4 GB at context 8192. Gemini stays the default. The silent miss exposed the hint weakness |
| 10 | PO and invoice layout variants | Done: three layouts (doc_variant 1 to 3) |
| 11 | ground_truth.py for all four clause types | Done |
| 12 | Dataset sanity tests for all specs | Done in test_spec_generator.py |
| 29 | RETRIEVAL_QUERIES defined twice | Done: legal_extractor.py owns RETRIEVAL_QUERIES (a tuple of queries per clause type) and retrieve(); eval/diagnose.py and eval/retrieval_eval.py import them. retrieval_eval.py not re-run yet (item 23) |
| 31 | Run `ruff check .` and `ruff format .` | Done: all checks pass, line-length 100 in pyproject.toml; run `ruff check . --fix --unsafe-fixes`, `ruff format .`, `ruff check .` after every new file |
| 39 | Hard categories on Tier A (unit_price, decoy, multi_breach) | Done: 58/58 on gemini-3.1-flash-lite |
| 47 | Grounding blind spot: one number in two roles (percent 8 and cap 8) | Done for the cap: if cap_percent equals percent, the quote must write that percentage at least twice (percent_count in grounding.py). Other double roles are not checked |
| 48 | Defined terms: tb_04 penalty clause says "after the Delivery Deadline", date in clause 5.1 | Done: the date clause ranked 14 for the penalty query, so late_penalty uses a second query (retrieve() adds 3 chunks). The form has deadline_quote and the rule keeps deadline_source. The date is accepted in three cases: written in the penalty quote; in a deadline quote that sits in the SAME clause (tb_06, tb_12); or in another clause that defines a date term, for example (the "Delivery Deadline"), which the penalty quote uses (tb_04, tb_09). Decoy clauses cannot borrow a date. Limits: item 55 |
| 49 | SILENT MISS tb_04 unit_price (clause 7.1, page 4) | Done: eval/diagnose.py showed the clause at rank 8 while TOP_K was 5. Fixed by rewording the unit_price query and TOP_K 5 to 8. Safety net added: keywords found but no rule extracted = "needs review" issue, never silence |
| 50 | Save raw model answers per call in the eval cache | Done: every cached result has raw_answers (task, chunk ids sent, seconds, raw text) |
| 51 | Measure Agent 1 on Tier B | Done: see Day 12 and Day 14 below |
| 53 | Tier A re-run with the new code | Done on Day 12 and again on Day 14 from an emptied cache: 31 contracts, 58 rules, 58 correct, 0 wrong, 0 refused, 0 silent, 0 spurious, 0 review issues; field 1.00, page 1.00, quote 0.93 |
| 54 | HINTS untested, false alarms, missed alarms | Done: hint_fires() in legal_extractor.py with its own tests; eval/hint_check.py measures all four on every contract without a model |
| 59 | tb_06 late_penalty refused: values right, quote held only the penalty sentence | Done: the late_penalty task asks for every sentence that states the percentage, the cap or the grace period (see item 64 for the wording that replaced the first version) |
| 63 | tb_09 late_penalty refused: "Quote not found" | Done: the model joined the date clause and the penalty clause with "..." and grounding refused it. The task now says the quote is ONE continuous passage of ONE clause, never joined and never with "...". test_quote_stitching.py |
| 64 | The fix of item 63 broke tb_06 and tb_12 | Done: the new wording told the model to keep the date out of the quote, and in those contracts the date sits in the neighbouring sentence of the same clause, which has no defined term. Fix: the date may come from a deadline quote in the SAME clause (item 48) and the task wording was rewritten. test_deadline_same_clause.py |
| 65 | tb_04 wrong cap_percent 10 for a flat 10% penalty | Done: refused for review instead of passed (item 47). The decision to drop the cap is item 46 |

## Checkpoints
- Day 12: Agent 1 numbers on Tier A and Tier B: done
- Day 13: buffer day: Ollama experiment, safety-net hints, ruff: done
- Day 14: untouched test set tb_09 to tb_12, three fixes, regression on Tier A and Tier B: done
- Day 15: tb_13 to tb_16 run ONCE (item 58) with items 57, 23, 38 and 46, in half a day at most. Then Week 3 (Agent 2) starts; do not add more Agent 1 work before it
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
- Day 12: Agent 1 evaluation finished. A date written in another clause now works (second retrieval query for late_penalty, deadline_quote in the form, deadline_source on the rule, defined-term link check in grounding.py). Review hints tightened and tested (hint_fires); diagnose and retrieval_eval share retrieve() with Agent 1; the eval cache keeps raw model answers with seconds per call. tb_05 to tb_08 written and checked. tb_06 fixed by asking for every value sentence in the late_penalty task. Final numbers on the same code: Tier A (31 contracts, 58 rules): 58 correct, 0 issues; Tier B (8 contracts, 20 rules): 20 correct, 0 issues. 186 tests
- Day 13: Ollama provider (llm/ollama.py, OLLAMA_* settings, --provider flag, per-call timing printed) and the experiment with qwen2.5:3b on Tier B: 4 of 20 rules correct, 0 wrong, 15 refused, 1 silent miss, 94 s per contract on CPU (2.4 GB). Gemini stays the default; the small model showed that grounding and the safety net turn failures into "needs review". The silent miss (tb_08 says "volume reduction") led to eval/hint_check.py: hints now work in either word order and catch reduction and rebate. Ruff: all checks pass, 63 files formatted (line-length 100). 202 tests
- Day 14: a fresh test set, tb_09 to tb_12 (Claude and ChatGPT, prompts asking for hard cases: a date only in a defined term, a volume rule without the word "discount", a contract with no penalty and no volume rule but with decoys, penalty and price spread over several sentences), checked with check_contract and frozen in git before Agent 1 ran. First run on them: 12 of 13 rules correct, 0 wrong (tb_09 refused: the model joined two clauses with "..."); that first result is kept in eval/results/first_run_before_stitching_fix. The fix for tb_09 broke tb_06 and tb_12 in the full Tier B run (items 63 and 64), fixed the same day, and a cap equal to the percentage now needs two mentions (item 65). Final numbers on the same code: Tier B (12 contracts, 33 rules): 32 correct, 0 wrong, 0 silent, 0 spurious, 1 refused (tb_04, the invented cap, caught); Tier A from an emptied cache (31 contracts, 58 rules): 58 correct, 0 issues; hint_check on 43 contracts: 0 and 0. 217 tests. Not a clean test any more: tb_09 to tb_12 were looked at while fixing, so tb_13 to tb_16 are the next untouched batch