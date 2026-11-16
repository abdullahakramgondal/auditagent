import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createAudit, type CreateAuditInput } from '@/api/audits'
import { auditKeys } from '@/api/queryKeys'

/**
 * Starts an audit. The history and the dashboard numbers are refreshed through their query keys
 * (features never import each other). Going to the audit page is done by the component that calls
 * this, with the id of the answer.
 */
export function useCreateAudit() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: CreateAuditInput) => createAudit(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: auditKeys.list() })
      void queryClient.invalidateQueries({ queryKey: auditKeys.summary() })
    },
  })
}