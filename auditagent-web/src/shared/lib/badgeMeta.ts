import type { AuditStatus, JobState } from '@/api/types'
import { statusMeta } from './statusMeta'

export type Badge = {
  label: string
  className: string
  /** Set only for a finished audit: it decides the icon. */
  status: AuditStatus | null
  /** True while the job is still working. */
  busy: boolean
}

const NEUTRAL = 'bg-slate-100 border-slate-400 text-slate-800'

/** How a row of the history looks. Only a finished audit gets a verdict colour; the rest is neutral. */
export function badgeOf(state: JobState, status: AuditStatus | null): Badge {
  if (state === 'done' && status) {
    const { label, className } = statusMeta[status]
    return { label, className, status, busy: false }
  }
  if (state === 'queued') return { label: 'Waiting', className: NEUTRAL, status: null, busy: true }
  if (state === 'running') return { label: 'Running', className: NEUTRAL, status: null, busy: true }
  if (state === 'failed') return { label: 'Failed', className: NEUTRAL, status: null, busy: false }
  return { label: 'Finished', className: NEUTRAL, status: null, busy: false }
}