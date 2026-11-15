import { HistoryView } from '@/features/history'

export function HistoryPage() {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">Audit history</h1>
      <HistoryView />
    </div>
  )
}