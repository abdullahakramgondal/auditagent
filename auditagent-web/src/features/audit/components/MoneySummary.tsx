import { formatPkr } from '@/shared/lib/money'

type Props = {
  billedTotal: string | null
  correctPayable: string | null
  totalDifference: string | null
  provisional: boolean
}

function Card({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <div
      className={`rounded-lg border bg-white p-4 md:p-6 ${
        strong ? 'order-first border-slate-900 sm:order-none' : 'border-slate-200'
      }`}
    >
      <dt className="text-sm text-slate-600">{label}</dt>
      <dd className="mt-1 text-2xl font-semibold tabular-nums md:text-3xl">{value}</dd>
    </div>
  )
}

export function MoneySummary({ billedTotal, correctPayable, totalDifference, provisional }: Props) {
  return (
    <section aria-label="Money" className="flex flex-col gap-2">
      <dl className="grid gap-4 sm:grid-cols-3">
        <Card label="Billed total" value={formatPkr(billedTotal)} />
        <Card label="Correct payable" value={formatPkr(correctPayable)} />
        <Card label="Over-billed" value={formatPkr(totalDifference)} strong />
      </dl>
      {provisional && (
        <p className="text-sm text-amber-900">
          These amounts may be incomplete: something could not be proven. See the reasons to check.
        </p>
      )}
    </section>
  )
}