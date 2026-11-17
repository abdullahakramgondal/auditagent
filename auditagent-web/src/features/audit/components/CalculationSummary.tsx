import type { CalcStep } from '@/api/types'

const AMOUNT_TONE: Record<CalcStep['kind'], string> = {
  start: 'text-slate-900',
  base: 'text-slate-900',
  minus: 'text-red-700',
  result: 'text-green-800',
  difference: 'text-red-700',
}

/** The sums behind the verdict, written by the backend: the screen only shows them. */
export function CalculationSummary({ steps }: { steps: CalcStep[] }) {
  if (steps.length === 0) return null
  return (
    <section aria-labelledby="calc-heading" className="flex flex-col gap-3">
      <h2 id="calc-heading" className="text-lg font-semibold">
        How we worked it out
      </h2>
      <p className="text-sm text-slate-600">Step by step, with the numbers of your documents.</p>
      <ol className="rounded-xl bg-white ring-1 ring-slate-200">
        {steps.map((step, index) => (
          <li
            key={`${step.kind}-${index}`}
            className={`flex flex-col gap-1 border-b border-slate-200 p-4 last:border-b-0 sm:flex-row sm:items-start sm:justify-between ${
              step.kind === 'result' ? 'bg-slate-50' : ''
            }`}
          >
            <div>
              <p className="font-medium">{step.label}</p>
              <p className="text-sm text-slate-600">{step.detail}</p>
            </div>
            <p className={`font-semibold tabular-nums ${AMOUNT_TONE[step.kind]}`}>
              {step.amount_text}
            </p>
          </li>
        ))}
      </ol>
    </section>
  )
}