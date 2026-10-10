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
contract amendments, non-English contracts, user login
Non-integer quantities (e.g. kilograms or meters)
whole-unit quantities only
Grace days: per-day penalty counts only days beyond the grace period; flat penalty applies only if delay exceeds the grace period.

## Done means
One case runs end to end, then 30 synthetic sets are evaluated.