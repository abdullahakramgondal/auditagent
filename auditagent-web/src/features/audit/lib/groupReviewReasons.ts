import type { ReviewReason } from '@/api/types'

type Source = ReviewReason['source']

const ORDER: Source[] = ['contract', 'invoice', 'purchase_order', 'audit']

export const sourceLabels: Record<Source, string> = {
  contract: 'Contract',
  invoice: 'Invoice',
  purchase_order: 'Purchase order',
  audit: 'Audit',
}

export type ReasonGroup = { source: Source; label: string; reasons: ReviewReason[] }

/** The reasons grouped by document in a fixed order; a document without reasons is left out. */
export function groupReviewReasons(reasons: ReviewReason[]): ReasonGroup[] {
  return ORDER.map((source) => ({
    source,
    label: sourceLabels[source],
    reasons: reasons.filter((reason) => reason.source === source),
  })).filter((group) => group.reasons.length > 0)
}