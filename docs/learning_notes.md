# Day 3 notes (my own words)
1. Each wording variant must contain the rule's numbers, otherwise the PDF would not match the spec.
2. Decoy clauses (liability 10%) make Agent 1's job realistic, so the evaluation is not too easy.
3. Ground truth is computed separately so the rule engine cannot copy a mistake from it.
4. The page comes from re-reading the PDF so it reflects where the clause really landed.




# Day 14 notes (my own words)
12. A prompt has no compiler. One sentence fixed tb_09 and broke tb_06 and tb_12 within the hour, and only the full Tier B run showed it. After every prompt change I run all contracts, not only the one that failed.
13. Keep the first result on contracts nobody has seen (12 of 13). After I fix a failure on them they are no longer unseen, so that first number is the honest one.
14. A quote must be one continuous passage of the contract. Two clauses joined with "..." is not a quote, and grounding refuses it.
15. Where a value may come from is a design choice: the quote itself, a neighbouring sentence of the same clause, or another clause that defines a term the quote uses. Every time I widened it, I added a test that the decoy still fails.
16. The same wrong value in two different contracts is a habit of the model, not bad luck. I wrote a deterministic check for it (a cap equal to the percentage must be written twice) instead of changing the prompt again.
17. "Saved result reused" next to every contract means nothing was run. rmdir /s /q is a cmd command; in PowerShell I use Remove-Item -Recurse -Force. Twice I mistook an old cache for a new result, so I check that every contract says "done in".