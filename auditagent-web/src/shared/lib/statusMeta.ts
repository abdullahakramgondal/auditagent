import type { AuditStatus } from '@/api/types'

type StatusMeta = { label: string; className: string }

/** One map for the look of a status. Record<AuditStatus, ...> makes the build fail if a status is added. */
export const statusMeta: Record<AuditStatus, StatusMeta> = {
  COMPLIANT: {
    label: 'Compliant',
    className: 'bg-green-50 border-green-600 text-green-900',
  },
  NON_COMPLIANT: {
    label: 'Non-compliant',
    className: 'bg-red-50 border-red-600 text-red-900',
  },
  NEEDS_REVIEW: {
    label: 'Needs human review',
    className: 'bg-amber-50 border-amber-500 text-amber-950',
  },
}