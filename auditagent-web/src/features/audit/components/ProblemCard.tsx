import type { PlainProblem } from '@/api/types'

/** One thing that is wrong, in plain words, with the sentence of the contract under it. */
export function ProblemCard({ number, problem }: { number: number; problem: PlainProblem }) {
  return (
    <li className="rounded-xl bg-white p-5 ring-1 ring-slate-200 md:p-6">
      <div className="flex flex-col gap-1 border-b border-slate-200 pb-3 sm:flex-row sm:items-start sm:justify-between">
        <h3 className="text-base font-semibold md:text-lg">
          {number}. {problem.title}
        </h3>
        <p className="font-semibold tabular-nums text-red-700">{problem.amount_text}</p>
      </div>
      <div className="mt-3 flex flex-col gap-2 text-base">
        {problem.paragraphs.map((text, index) => (
          <p key={index}>{text}</p>
        ))}
      </div>
      <div className="mt-4 rounded-lg bg-slate-100 p-4">
        <p className="text-sm text-slate-600">What the contract says (page {problem.page})</p>
        <blockquote className="mt-1 italic">{problem.quote}</blockquote>
      </div>
    </li>
  )
}