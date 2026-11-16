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
      className={`rounded-xl bg-white p-4 md:p-6 ${
        strong ? 'order-first ring-2 ring-slate-900 sm:order-none' : 'ring-1 ring-slate-200'
      }`}
    >
      <dt className="text-sm text-slate-600">{label}</dt>
      <dd className="mt-1 text-2xl font-semibold tabular-nums md:text-3xl">{value}</dd>
    </div>
  )
}

export function MoneySummary({ billedTotal, correctPayable, totalDifference, provisional }: Props) {
  return (
    <section aria-label="The money" className="flex flex-col gap-2">
      <dl className="grid gap-4 sm:grid-cols-3">
        <Card label="The vendor is asking for" value={formatPkr(billedTotal)} />
        <Card label="The right amount is" value={formatPkr(correctPayable)} />
        <Card label="Too much" value={formatPkr(totalDifference)} strong />
      </dl>
      {provisional && (
        <p className="text-sm text-amber-900">
          These amounts may be incomplete, because something could not be checked.
        </p>
      )}
    </section>
  )
}