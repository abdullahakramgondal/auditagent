import { resultJsonUrl } from '@/api/audits'
import { ErrorNotice } from '@/shared/ui/ErrorNotice'
import { useAudit } from '../hooks/useAudit'

/** Placeholder until M4: shows the state of the job, polled from the real backend. */
export function AuditView({ id }: { id: string }) {
  const job = useAudit(id)

  if (job.isPending) return <p>Loading…</p>
  if (job.isError) {
    return <ErrorNotice message={job.error.message} onRetry={() => void job.refetch()} />
  }

  const { state, status, error } = job.data
  return (
    <div className="flex flex-col gap-3">
      <h1 className="text-2xl font-semibold tracking-tight">Audit</h1>
      <p className="text-sm text-slate-600">Audit {id}</p>
      <p>
        State: <strong>{state}</strong>
        {status && (
          <>
            {' '}
            · Status: <strong>{status}</strong>
          </>
        )}
      </p>
      {error && <ErrorNotice message={error} />}
      {state === 'done' && (
        <a className="text-blue-700 underline" href={resultJsonUrl(id)}>
          Download result JSON
        </a>
      )}
    </div>
  )
}