import { Link } from 'react-router'
import { EmptyState } from '@/shared/ui/EmptyState'
import { ErrorNotice } from '@/shared/ui/ErrorNotice'
import { useAuditSummary } from '../hooks/useAuditSummary'
import { SummaryCards } from './SummaryCards'

function Skeleton() {
  return (
    <div>
      <span className="sr-only">Loading your numbers…</span>
      <div aria-hidden="true" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[0, 1, 2, 3].map((card) => (
          <div key={card} className="h-28 animate-pulse rounded-xl bg-slate-200" />
        ))}
      </div>
    </div>
  )
}

/** Loading, error, empty and success: the four states of the numbers. */
export function SummaryView() {
  const summary = useAuditSummary()

  let content
  if (summary.isPending) {
    content = <Skeleton />
  } else if (summary.isError) {
    content = <ErrorNotice message={summary.error.message} onRetry={() => void summary.refetch()} />
  } else if (summary.data.total === 0) {
    content = (
      <EmptyState title="You have not checked any invoice yet">
        <Link to="/new" className="text-blue-700 underline">
          Check your first invoice
        </Link>
      </EmptyState>
    )
  } else {
    content = <SummaryCards summary={summary.data} />
  }

  return (
    <section aria-labelledby="summary-heading" className="flex flex-col gap-4">
      <h2 id="summary-heading" className="text-lg font-semibold">
        Your audits so far
      </h2>
      {content}
    </section>
  )
}