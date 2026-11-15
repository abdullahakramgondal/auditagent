import type { AuditStatus, JobState } from '@/api/types'
import { badgeOf } from '@/shared/lib/badgeMeta'
import { StatusIcon } from './StatusIcon'

/** Icon (or a dot) and text together: the colour is never the only signal. */
export function StatusBadge({ state, status }: { state: JobState; status: AuditStatus | null }) {
  const badge = badgeOf(state, status)
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-sm font-medium ${badge.className}`}
    >
      {badge.status ? (
        <StatusIcon status={badge.status} className="size-4 shrink-0" />
      ) : (
        <span
          aria-hidden="true"
          className={`size-2 shrink-0 rounded-full bg-current ${badge.busy ? 'animate-pulse' : ''}`}
        />
      )}
      {badge.label}
    </span>
  )
}