import { ErrorNotice } from '@/shared/ui/ErrorNotice'
import { useAudit } from '../hooks/useAudit'
import { useAuditResult } from '../hooks/useAuditResult'
import { AuditResultView } from './AuditResultView'
import { FailedView } from './FailedView'
import { ProgressView } from './ProgressView'

/** The one place that decides which screen an audit shows: loading, error, failed, running or done. */
export function AuditView({ id }: { id: string }) {
  const job = useAudit(id)
  const isDone = job.data?.state === 'done'
  const result = useAuditResult(id, { enabled: isDone })

  if (job.isPending) return <p role="status">Loading…</p>
  if (job.isError) {
    return <ErrorNotice message={job.error.message} onRetry={() => void job.refetch()} />
  }
  if (job.data.state === 'failed') return <FailedView job={job.data} />
  if (!isDone) return <ProgressView job={job.data} />

  if (result.isPending) return <p role="status">Loading the result…</p>
  if (result.isError) {
    return (
      <ErrorNotice
        message={`${result.error.message} (audit ${id})`}
        onRetry={() => void result.refetch()}
      />
    )
  }
  return <AuditResultView result={result.data} />
}