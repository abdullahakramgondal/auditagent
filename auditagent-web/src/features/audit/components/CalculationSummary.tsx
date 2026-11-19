import type { CalcStep } from '@/api/types'

const AMOUNT_TONE: Record<CalcStep['kind'], string> = {
  start: 'text-slate-900',
  base: 'text-slate-900',
  minus: 'text-red-700',
  result: 'text-green-800',
  difference: 'text-red-700',
}

/** The sums behind the verdict as a table, written by the backend: the screen only shows them. */
export function CalculationSummary({ steps }: { steps: CalcStep[] }) {
  if (steps.length === 0) return null
  return (
    <section aria-labelledby="calc-heading" className="flex flex-col gap-3">
      <h2 id="calc-heading" className="text-lg font-semibold">
        How we worked it out
      </h2>
      <p className="text-sm text-slate-600">Step by step, with the numbers of your documents.</p>
      <div className="overflow-x-auto rounded-xl bg-white ring-1 ring-slate-200">
        <table className="w-full text-left text-sm md:text-base">
          <caption className="sr-only">How the right amount was worked out, step by step</caption>
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-sm text-slate-600">
              <th scope="col" className="px-4 py-3 font-medium">
                Step
              </th>
              <th scope="col" className="px-4 py-3 font-medium">
                How we got it
              </th>
              <th scope="col" className="px-4 py-3 text-right font-medium">
                Amount
              </th>
            </tr>
          </thead>
          <tbody>
            {steps.map((step, index) => (
              <tr
                key={`${step.kind}-${index}`}
                className={`border-b border-slate-200 last:border-b-0 ${
                  step.kind === 'result' ? 'bg-slate-50' : ''
                }`}
              >
                <th scope="row" className="px-4 py-3 align-top font-medium">
                  {step.label}
                </th>
                <td className="px-4 py-3 align-top text-slate-600">{step.detail}</td>
                <td
                  className={`whitespace-nowrap px-4 py-3 text-right align-top font-semibold tabular-nums ${AMOUNT_TONE[step.kind]}`}
                >
                  {step.amount_text}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}