import { Link } from 'react-router'
import type { JobInfo } from '@/api/types'
import { formatDateTime } from '@/shared/lib/dates'
import { useNow } from '../hooks/useNow'
import { elapsedMs, formatElapsed, isSlow } from '../lib/elapsed'

/**
 * The backend gives no step of the work, only queued or running. The live region changes only when
 * the state changes; the elapsed time is outside it, so a screen reader is not read to every second.
 */
export function ProgressView({ job }: { job: JobInfo }) {
  const now = useNow(1000)
  const queued = job.state === 'queued'

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Audit in progress</h1>
        <p className="mt-1 text-sm text-slate-600">
          Audit {job.audit_id} · started {formatDateTime(job.created_at)}
        </p>
      </div>

      <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white p-4">
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          fill="none"
          className="size-5 shrink-0 animate-spin text-slate-700"
        >
          <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" opacity="0.25" />
          <path d="M21 12a9 9 0 00-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
        </svg>
        <div>
          <p aria-live="polite" className="font-medium">
            {queued ? 'Waiting to start…' : 'Reading the documents and checking the invoice…'}
          </p>
          <p className="text-sm text-slate-600">
            Running for {formatElapsed(elapsedMs(job.created_at, now))}
          </p>
        </div>
      </div>

      {isSlow(job.created_at, now) && (
        <p role="note" className="rounded-lg bg-slate-100 p-4 text-sm">
          This is taking longer than usual. You can leave this page and open the audit later from{' '}
          <Link to="/history" className="text-blue-700 underline">
            History
          </Link>
          .
        </p>
      )}
    </div>
  )
}