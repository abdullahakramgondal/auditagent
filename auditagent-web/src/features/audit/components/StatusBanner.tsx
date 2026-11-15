import type { AuditStatus } from '@/api/types'
import { statusMeta } from '@/shared/lib/statusMeta'
import { StatusIcon } from '@/shared/ui/StatusIcon'

/** Colour, icon and text together: the colour is never the only signal. */
export function StatusBanner({ status, message }: { status: AuditStatus; message: string }) {
  const { label, className } = statusMeta[status]
  return (
    <section
      role="status"
      aria-label="Audit status"
      className={`flex items-start gap-3 rounded-lg border-l-4 p-4 ${className}`}
    >
      <StatusIcon status={status} className="mt-0.5 size-5 shrink-0" />
      <div>
        <p className="font-semibold">{label}</p>
        <p className="text-sm">{message}</p>
      </div>
    </section>
  )
}