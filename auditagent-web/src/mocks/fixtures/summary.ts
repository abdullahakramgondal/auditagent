// GET /audits/summary for the five audits of history.ts: one of each kind.
export const summary: Record<string, unknown> = {
  total: 5,
  in_progress: 1,
  failed: 1,
  compliant: 1,
  non_compliant: 1,
  needs_review: 1,
  total_difference: '1041250.00',
}