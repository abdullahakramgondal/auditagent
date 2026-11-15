import { useQuery } from '@tanstack/react-query'
import { getAuditResult } from '@/api/audits'
import { auditKeys } from '@/api/queryKeys'

/** The result is read once the job is done; a finished audit never changes. */
export function useAuditResult(id: string, options: { enabled: boolean }) {
  return useQuery({
    queryKey: auditKeys.result(id),
    queryFn: () => getAuditResult(id),
    enabled: options.enabled,
    staleTime: Infinity,
  })
}