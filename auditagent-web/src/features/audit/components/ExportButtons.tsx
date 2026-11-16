import { reportPdfUrl, resultJsonUrl } from '@/api/audits'

// Two complete sets of classes. Never put bg-white and bg-slate-900 on one element: Tailwind
// picks the winner by the order of its stylesheet, not by the order here (white text on white).
const BASE = 'rounded-md border px-3 py-2 text-sm font-medium'
const PRIMARY = `${BASE} border-slate-900 bg-slate-900 text-white hover:bg-slate-700`
const SECONDARY = `${BASE} border-slate-300 bg-white text-slate-900 hover:bg-slate-100`

/** The backend sends both files as attachments, so a plain link downloads them. */
export function ExportButtons({ id }: { id: string }) {
  return (
    <div className="flex flex-wrap gap-2">
      <a href={reportPdfUrl(id)} className={PRIMARY}>
        Download PDF report
      </a>
      <a href={resultJsonUrl(id)} className={SECONDARY}>
        Download JSON
      </a>
    </div>
  )
}