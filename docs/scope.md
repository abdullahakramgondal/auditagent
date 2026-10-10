# AuditAgent AI: Scope (v1)

Industry: IT procurement in Pakistani software houses
Inputs: Contract PDF, PO PDF, Invoice PDF (text-based PDFs only)

## Clause types supported in v1
1. Late-delivery penalty
   - flat percentage, or per-day rate with a maximum cap
   - optional grace days
2. Volume / tier discount (quantity threshold -> discount %)
3. Payment terms (Net N days; invoice due date must match)
4. Agreed unit price (invoice rate must not exceed contract rate)

## Calculation rules
- The penalty percentage is applied to the invoice total.
- Days late = delivery date minus deadline. If negative, it is set to zero.
- Grace days: a per-day penalty counts only the days beyond the grace period;
  a flat penalty applies only if the delay exceeds the grace period.
- Money is handled as Decimal and computed by code, never by the LLM.

## Output
- Status: COMPLIANT / NON_COMPLIANT / NEEDS_REVIEW
- Findings list. Each finding has: clause text, contract page,
  expected amount, billed amount, difference in PKR

## Why only these clauses
An audit needs a contract rule AND a matching fact in the PO or invoice.
Clauses such as confidentiality, termination, warranty, liability cap
and SLA uptime cannot be verified from an invoice, so they are out of scope.

## Out of scope for v1
Scanned PDFs (OCR), multiple currencies, tax rules,
contract amendments, non-English contracts, user login,
non-integer quantities (whole units only, e.g. no kilograms or meters)

## Done means
One case runs end to end, then 30 synthetic sets are evaluated.