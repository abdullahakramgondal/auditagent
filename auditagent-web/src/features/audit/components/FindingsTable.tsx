import type { Finding } from '@/api/types'
import { FindingRow } from './FindingRow'

export function FindingsTable({ findings }: { findings: Finding[] }) {
  return (
    <section aria-labelledby="findings-heading" className="flex flex-col gap-3">
      <h2 id="findings-heading" className="text-lg font-semibold">
        Findings ({findings.length})
      </h2>
      {findings.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-300 bg-white p-4 text-sm text-slate-600">
          No billing differences found.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white px-4">
          <table className="w-full text-sm md:text-base">
            <thead>
              <tr className="border-b text-left text-sm text-slate-600">
                <th scope="col" className="py-3 pr-4 font-medium">
                  Clause
                </th>
                <th scope="col" className="py-3 pr-4 text-right font-medium">
                  Difference
                </th>
                <th scope="col" className="py-3">
                  <span className="sr-only">Details</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {findings.map((finding, index) => (
                <FindingRow key={`${finding.clause_type}-${index}`} finding={finding} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}