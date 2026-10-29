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

# Day 16 notes (my own words)
24. A value must be proven where the document puts it, not just somewhere on the page. A date has to sit on a line with its own label. If the model swaps the invoice date and the delivery date, both dates are still on the page, but the delivery date decides the late penalty, so a swap must be refused.
25. A wrong invoice is information for the audit, not a program error. If a row does not equal quantity times price, or the total does not equal the rows plus the adjustments, I return the data with an issue. If a value cannot be proven at all, I return no document and the reason.
26. "None" is also a claim. If the model says there is no delivery date but the document shows a date next to its label, I refuse it for review. It is the same idea as Agent 1's empty answer: silence is not an answer.
27. 62 of 62 on documents that my own generator wrote proves the plumbing and the three layouts, not the real world. It is the same lesson as Agent 1 on Day 9. The real test is messy documents that I did not generate.
28. The code hash covers shared folders, so changing a schema for Agent 2 made Agent 1 run again. That cost a few minutes, but a saved result can never be older than the code it claims to come from.

# Day 18 notes (my own words)
29. A wait that nobody sees looks like a frozen program. Now every retry says what failed and how long it waits. On the same day Gemini was unavailable for hours, and I could tell it was the provider and not my code.
30. A value that the model computed is not a value that the document wrote. On cb_07 the invoice only said "Net 30 days" and the model added 30 days to the invoice date. The date was probably right, and I still refuse it, because the audit must rest on what is written. If I need Net 30, I will read the terms and let the code compute the date.
31. Eight documents with one new shape each showed three real gaps (a label, a wrapped item name, a computed date) and each gap has one cause. If I had put all eight shapes in one document, I would not know which one broke it.
32. Refused is not the same as wrong. 5 correct, 3 refused and 0 wrong means the system stayed careful: it asks a human instead of guessing. The recall of 0.62 is the price, and Week 4 turns every refusal into a review reason.
33. I wrote down what I expected before the run, and I was right about four of the five refusals. The surprise (cb_07) taught me more than all the correct guesses.