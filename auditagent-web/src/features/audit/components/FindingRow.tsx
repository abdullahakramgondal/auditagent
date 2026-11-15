import { useId, useState } from 'react'
import type { Finding } from '@/api/types'
import { formatPkr } from '@/shared/lib/money'
import { clauseLabels } from '../lib/clauseLabels'

/** A table row that expands to the clause text, its page and the three amounts. */
export function FindingRow({ finding }: { finding: Finding }) {
  const [open, setOpen] = useState(false)
  const detailsId = useId()
  const label = clauseLabels[finding.clause_type]

  return (
    <>
      <tr className="border-b">
        <th scope="row" className="py-3 pr-4 text-left font-medium">
          {label}
        </th>
        <td className="py-3 pr-4 text-right tabular-nums">{formatPkr(finding.difference)}</td>
        <td className="py-3 text-right">
          <button
            type="button"
            aria-expanded={open}
            aria-controls={detailsId}
            aria-label={`${open ? 'Hide' : 'Show'} clause for ${label}`}
            onClick={() => setOpen((value) => !value)}
            className="rounded-md px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-slate-100"
          >
            {open ? 'Hide' : 'Show'} clause
          </button>
        </td>
      </tr>
      <tr id={detailsId} hidden={!open}>
        <td colSpan={3} className="bg-slate-100 p-4">
          <p className="text-sm">{finding.description}</p>
          <blockquote className="mt-3 border-l-4 border-slate-400 pl-4 italic">
            {finding.source.text}
          </blockquote>
          <p className="mt-1 text-sm text-slate-600">Contract, page {finding.source.page}</p>
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-slate-600">Expected</dt>
              <dd className="tabular-nums">{formatPkr(finding.expected_amount)}</dd>
            </div>
            <div>
              <dt className="text-slate-600">Billed</dt>
              <dd className="tabular-nums">{formatPkr(finding.billed_amount)}</dd>
            </div>
            <div>
              <dt className="text-slate-600">Difference</dt>
              <dd className="font-semibold tabular-nums">{formatPkr(finding.difference)}</dd>
            </div>
          </dl>
        </td>
      </tr>
    </>
  )
}