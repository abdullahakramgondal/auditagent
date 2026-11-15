import type { ReviewReason } from '@/api/types'
import { fieldLabel } from '../lib/clauseLabels'
import { groupReviewReasons } from '../lib/groupReviewReasons'

/** Always visible, never in a collapsed panel: the reasons are the most important part of a review. */
export function ReviewReasons({ reasons }: { reasons: ReviewReason[] }) {
  return (
    <section aria-labelledby="reasons-heading" className="flex flex-col gap-3">
      <h2 id="reasons-heading" className="text-lg font-semibold">
        Reasons to check
      </h2>
      {groupReviewReasons(reasons).map((group) => (
        <div key={group.source}>
          <h3 className="text-sm font-semibold text-slate-700">{group.label}</h3>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
            {group.reasons.map((reason, index) => (
              <li key={`${reason.field}-${index}`}>
                {reason.field && <span className="font-medium">{fieldLabel(reason.field)}: </span>}
                {reason.reason}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  )
}