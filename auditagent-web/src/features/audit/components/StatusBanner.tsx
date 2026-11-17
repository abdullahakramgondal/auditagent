import type { AuditStatus } from '@/api/types'
import { statusMeta } from '@/shared/lib/statusMeta'
import { StatusIcon } from '@/shared/ui/StatusIcon'

type Props = { status: AuditStatus; headline: string; advice: string }

/** The answer in one look: colour, icon, the status label and plain words together. */
export function StatusBanner({ status, headline, advice }: Props) {
  const { className, label } = statusMeta[status]
  return (
    <section
      role="status"
      aria-label="Result"
      className={`flex items-start gap-4 rounded-xl border-l-8 p-5 md:p-6 ${className}`}
    >
      <StatusIcon status={status} className="mt-1 size-7 shrink-0" />
      <div>
        <p className="text-sm font-semibold uppercase tracking-wide">{label}</p>
        <p className="text-xl font-semibold md:text-2xl">{headline}</p>
        <p className="mt-1 text-base md:text-lg">{advice}</p>
      </div>
    </section>
  )
}