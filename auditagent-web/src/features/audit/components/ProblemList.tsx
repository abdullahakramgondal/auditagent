import type { PlainProblem } from '@/api/types'
import { ProblemCard } from './ProblemCard'

/** The mistakes. When there are none, nothing is shown: "What we checked" says the rest. */
export function ProblemList({ problems }: { problems: PlainProblem[] }) {
  if (problems.length === 0) return null
  return (
    <section aria-labelledby="problems-heading" className="flex flex-col gap-3">
      <h2 id="problems-heading" className="text-lg font-semibold">
        What is wrong
      </h2>
      <ol className="flex flex-col gap-4">
        {problems.map((problem, index) => (
          <ProblemCard key={`${problem.clause_type}-${index}`} number={index + 1} problem={problem} />
        ))}
      </ol>
    </section>
  )
}