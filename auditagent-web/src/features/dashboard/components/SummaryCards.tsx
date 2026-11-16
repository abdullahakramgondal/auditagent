import type { Summary } from '@/api/types'
import { formatPkr } from '@/shared/lib/money'

type CardProps = { label: string; value: number; hint: string; tone: string }

function Card({ label, value, hint, tone }: CardProps) {
  return (
    <li className={`rounded-xl border-l-4 bg-white p-5 ring-1 ring-slate-200 ${tone}`}>
      <p className="text-sm font-medium text-slate-600">{label}</p>
      <p className="mt-1 text-3xl font-semibold tabular-nums">{value}</p>
      <p className="mt-1 text-sm text-slate-600">{hint}</p>
    </li>
  )
}

function plural(count: number, one: string, many: string): string {
  return count === 1 ? one : many
}

export function SummaryCards({ summary }: { summary: Summary }) {
  return (
    <div className="flex flex-col gap-4">
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card
          label="Invoices checked"
          value={summary.total}
          hint="in total"
          tone="border-slate-400"
        />
        <Card
          label="Correct invoices"
          value={summary.compliant}
          hint="matched the contract"
          tone="border-green-600"
        />
        <Card
          label="Invoices with a mistake"
          value={summary.non_compliant}
          hint="broke a rule of the contract"
          tone="border-red-600"
        />
        <Card
          label="Need a person"
          value={summary.needs_review}
          hint="could not be fully checked"
          tone="border-amber-500"
        />
      </ul>

      <div className="rounded-xl bg-slate-900 p-6 text-white">
        <p className="text-sm text-slate-300">Extra money that vendors charged, found so far</p>
        <p className="mt-1 text-3xl font-semibold tabular-nums md:text-4xl">
          {formatPkr(summary.total_difference)}
        </p>
      </div>

      {summary.in_progress > 0 && (
        <p role="status" className="text-sm text-slate-600">
          {summary.in_progress} {plural(summary.in_progress, 'audit is', 'audits are')} still being
          checked.
        </p>
      )}
      {summary.failed > 0 && (
        <p className="text-sm text-slate-600">
          {summary.failed} {plural(summary.failed, 'audit', 'audits')} could not finish. You can
          find {plural(summary.failed, 'it', 'them')} in the history and try again.
        </p>
      )}
    </div>
  )
}