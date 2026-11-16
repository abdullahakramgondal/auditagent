import type { ReviewReason } from '@/api/types'
import { fieldLabel } from '../lib/clauseLabels'
import { groupReviewReasons } from '../lib/groupReviewReasons'

/** Always visible, never in a collapsed panel: this is the most important part of a review. */
export function ReviewReasons({ reasons }: { reasons: ReviewReason[] }) {
  return (
    <section aria-labelledby="reasons-heading" className="flex flex-col gap-3">
      <h2 id="reasons-heading" className="text-lg font-semibold">
        Things we could not check
      </h2>
      <p className="text-sm text-slate-600">
        The system did not guess. These points need a person to look at them.
      </p>
      {groupReviewReasons(reasons).map((group) => (
        <div key={group.source}>
          <h3 className="text-sm font-semibold text-slate-700">{group.label}</h3>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-base">
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