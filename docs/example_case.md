# Golden examples (worked by hand)

## Case A: Late delivery, penalty missed (NON_COMPLIANT)

| Document | What it says |
|---|---|
| Contract, page 4 | If delivery is later than 15 Oct 2026, a 10% penalty applies to the final invoice |
| Purchase Order | 10 servers x PKR 1,000,000 = PKR 10,000,000. Delivery due 15 Oct 2026 |
| Invoice | 10 servers x PKR 1,000,000 = PKR 10,000,000. Delivered 25 Oct 2026 |

Correct answer:
- Days late = 10
- Penalty = 10% of 10,000,000 = PKR 1,000,000
- Correct payable = PKR 9,000,000
- Billed = PKR 10,000,000, difference = PKR 1,000,000
- Status: NON_COMPLIANT

## Case B: Delivered on time (COMPLIANT)

Same contract and PO. Invoice says delivered 14 Oct 2026, total PKR 10,000,000.

Correct answer:
- Days late = 0, penalty = PKR 0
- Correct payable = PKR 10,000,000
- Status: COMPLIANT