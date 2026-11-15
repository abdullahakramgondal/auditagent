import { resultJsonUrl } from '@/api/audits'

/** The backend sends result.json as an attachment, so a plain link downloads it. */
export function ExportButtons({ id }: { id: string }) {
  return (
    <a
      href={resultJsonUrl(id)}
      className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium hover:bg-slate-100"
    >
      Download JSON
    </a>
  )
}