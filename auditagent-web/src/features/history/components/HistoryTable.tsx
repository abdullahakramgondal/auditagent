import { Link } from 'react-router'
import type { JobInfo } from '@/api/types'
import { formatDateTime } from '@/shared/lib/dates'
import { formatPkr } from '@/shared/lib/money'
import { StatusBadge } from '@/shared/ui/StatusBadge'

/** The date is a real link: it works from the keyboard and opens in a new tab. */
export function HistoryTable({ rows }: { rows: JobInfo[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white px-4">
      <table className="w-full text-sm md:text-base">
        <caption className="sr-only">Audit history, newest first</caption>
        <thead>
          <tr className="border-b text-left text-sm text-slate-600">
            <th scope="col" className="py-3 pr-4 font-medium">
              Date
            </th>
            <th scope="col" className="py-3 pr-4 font-medium">
              Model
            </th>
            <th scope="col" className="py-3 pr-4 font-medium">
              Status
            </th>
            <th scope="col" className="py-3 text-right font-medium">
              Difference
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.audit_id} className="border-b last:border-b-0">
              <th scope="row" className="py-3 pr-4 text-left font-medium">
                <Link
                  to={`/audits/${row.audit_id}`}
                  className="text-blue-700 underline-offset-2 hover:underline"
                >
                  {formatDateTime(row.created_at)}
                </Link>
              </th>
              <td className="py-3 pr-4 text-slate-700">{row.llm_model ?? row.model ?? '—'}</td>
              <td className="py-3 pr-4">
                <StatusBadge state={row.state} status={row.status} />
              </td>
              <td className="py-3 text-right tabular-nums">{formatPkr(row.total_difference)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}