# Dataset plan (30 synthetic cases)

| Category | Cases | Purpose |
|---|---|---|
| All compliant | 6 | No false alarms |
| Late penalty, flat % | 4 | Easy case |
| Late penalty, per-day + cap | 4 | Arithmetic test |
| Late but inside grace days (compliant) | 3 | Common mistake: penalty applied wrongly |
| Volume discount missed | 3 | Quantity vs threshold |
| Unit price above agreed rate | 3 | Unit price check |
| Wrong payment terms | 2 | Due date check |
| Multiple breaches in one case | 3 | Findings must agree |
| Decoy / tricky wording | 2 | Penalty-like text in the wrong clause |

Every case: 3 wording variants, 2 to 8 contract pages, varied items.
Ground truth comes from the spec file, never from the system under test.