import type { AuditStatus } from '@/api/types'

const PATHS: Record<AuditStatus, string> = {
  COMPLIANT:
    'M10 18a8 8 0 100-16 8 8 0 000 16zm3.7-9.3a1 1 0 00-1.4-1.4L9 10.6 7.7 9.3a1 1 0 00-1.4 1.4l2 2a1 1 0 001.4 0l4-4z',
  NON_COMPLIANT:
    'M10 18a8 8 0 100-16 8 8 0 000 16zM8.7 7.3a1 1 0 00-1.4 1.4L8.6 10l-1.3 1.3a1 1 0 101.4 1.4L10 11.4l1.3 1.3a1 1 0 001.4-1.4L11.4 10l1.3-1.3a1 1 0 00-1.4-1.4L10 8.6 8.7 7.3z',
  NEEDS_REVIEW:
    'M8.5 3.6a1.7 1.7 0 012.9 0l5.6 9.7A1.7 1.7 0 0115.6 16H4.4a1.7 1.7 0 01-1.5-2.7l5.6-9.7zM10 7a1 1 0 00-1 1v3a1 1 0 102 0V8a1 1 0 00-1-1zm0 7.5a1 1 0 100-2 1 1 0 000 2z',
}

/** The icon of a status. It is decorative: the status text always sits next to it. */
export function StatusIcon({ status, className }: { status: AuditStatus; className?: string }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 20 20" fill="currentColor" className={className}>
      <path fillRule="evenodd" clipRule="evenodd" d={PATHS[status]} />
    </svg>
  )
}