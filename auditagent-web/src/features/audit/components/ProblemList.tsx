import type { AuditStatus, PlainProblem } from '@/api/types'
import { ProblemCard } from './ProblemCard'

type Props = { problems: PlainProblem[]; status: AuditStatus }

export function ProblemList({ problems, status }: Props) {
  return (
    <section aria-labelledby="problems-heading" className="flex flex-col gap-3">
      <h2 id="problems-heading" className="text-lg font-semibold">
        What is wrong
      </h2>
      {problems.length > 0 ? (
        <ol className="flex flex-col gap-4">
          {problems.map((problem, index) => (
            <ProblemCard key={`${problem.clause_type}-${index}`} number={index + 1} problem={problem} />
          ))}
        </ol>
      ) : (
        <p className="rounded-xl border border-dashed border-slate-300 bg-white p-5 text-base">
          {status === 'COMPLIANT'
            ? 'Nothing is wrong. The invoice follows every rule that we found in the contract.'
            : 'No mistake was proven, but some things could not be checked (see the list of things we could not check).'}
        </p>
      )}
    </section>
  )
}