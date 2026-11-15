import type { ReactNode } from 'react'

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-start gap-2 rounded-lg border border-dashed border-slate-300 bg-white p-6">
      <p className="font-semibold">{title}</p>
      {children}
    </div>
  )
}