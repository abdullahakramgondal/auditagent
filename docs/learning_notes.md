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
# Day 15 notes (my own words)
18. A result saved on disk must say which code made it. I now store a hash of the Agent 1 code in every saved result and refuse to reuse a result from other code. The report says "ran now 16", so I can see how many contracts really ran. Twice before I mistook an old cache for a new result.
19. "The model is wrong" and "my checker cannot prove it" are different problems. On tb_14 and tb_16 the model gave the right answer; grounding had no way to link "clause 5.2" to the date clause. I fixed the checker, not the prompt.
20. A link between two clauses must be written in the contract: a defined term or a clause number. I never guess a link, and a wrong clause number is refused.
21. The same wrong value in four runs (a cap on a flat penalty) is a habit of the model. The scope says only a per-day penalty has a cap, so the cap is dropped by a rule in the code. It does not change the money maths.
22. I wrote my predictions before the run (tb_14 and tb_16 refused, the tb_16 hint misses, tb_13 correct). They were all right. Writing the guess first shows me what I really understand, and what I only hoped.
23. A batch of unseen contracts is used up by the first fix. I keep the first-run result of every batch (12 of 13, then 10 of 12, no wrong rule) and I keep one fresh batch for the final evaluation.