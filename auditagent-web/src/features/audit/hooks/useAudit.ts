import { useQuery } from '@tanstack/react-query'
import { getAuditState } from '@/api/audits'
import { auditKeys } from '@/api/queryKeys'
import type { JobState } from '@/api/types'

const POLL_MS = 2500

/** Poll every 2.5 seconds until the job is done or failed. */
export function auditRefetchInterval(state: JobState | undefined): number | false {
  return state === 'done' || state === 'failed' ? false : POLL_MS
}

export function useAudit(id: string) {
  return useQuery({
    queryKey: auditKeys.detail(id),
    queryFn: () => getAuditState(id),
    refetchInterval: (query) => auditRefetchInterval(query.state.data?.state),
  })
}