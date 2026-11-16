import { useQuery } from '@tanstack/react-query'
import { getSummary } from '@/api/audits'
import { auditKeys } from '@/api/queryKeys'
import type { Summary } from '@/api/types'

const POLL_MS = 5000

/** While an audit is still being checked, the numbers refresh by themselves. */
export function summaryRefetchInterval(summary: Summary | undefined): number | false {
  return summary && summary.in_progress > 0 ? POLL_MS : false
}

export function useAuditSummary() {
  return useQuery({
    queryKey: auditKeys.summary(),
    queryFn: () => getSummary(),
    refetchInterval: (query) => summaryRefetchInterval(query.state.data),
  })
}