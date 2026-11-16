import { Link } from 'react-router'
import { EmptyState } from '@/shared/ui/EmptyState'
import { ErrorNotice } from '@/shared/ui/ErrorNotice'
import { useAuditHistory } from '../hooks/useAuditHistory'
import { HistoryTable } from './HistoryTable'

function HistorySkeleton() {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <span className="sr-only">Loading history…</span>
      <div aria-hidden="true" className="flex flex-col gap-3">
        {[0, 1, 2, 3, 4].map((row) => (
          <div key={row} className="h-8 animate-pulse rounded bg-slate-100" />
        ))}
      </div>
    </div>
  )
}

/** Loading, error, empty and success: the four states of the history screen. */
export function HistoryView() {
  const history = useAuditHistory()

  if (history.isPending) return <HistorySkeleton />
  if (history.isError) {
    return <ErrorNotice message={history.error.message} onRetry={() => void history.refetch()} />
  }
  if (history.data.length === 0) {
    return (
      <EmptyState title="No audits yet">
        <Link to="/new" className="text-blue-700 underline">
          Start a new audit
        </Link>
      </EmptyState>
    )
  }
  return <HistoryTable rows={history.data} />
}
