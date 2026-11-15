import { useQuery } from '@tanstack/react-query'
import { listAudits } from '@/api/audits'
import { auditKeys } from '@/api/queryKeys'
import type { JobInfo } from '@/api/types'

const HISTORY_POLL_MS = 5000

/** While some audit is still queued or running, the list refreshes by itself. */
export function historyRefetchInterval(rows: JobInfo[] | undefined): number | false {
  const busy = rows?.some((row) => row.state === 'queued' || row.state === 'running')
  return busy ? HISTORY_POLL_MS : false
}

export function useAuditHistory() {
  return useQuery({
    queryKey: auditKeys.list(),
    queryFn: () => listAudits(),
    refetchInterval: (query) => historyRefetchInterval(query.state.data),
  })
}