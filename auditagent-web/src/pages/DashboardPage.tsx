import { HowItWorks, SummaryView, Welcome } from '@/features/dashboard'

export function DashboardPage() {
  return (
    <div className="flex flex-col gap-10">
      <Welcome />
      <SummaryView />
      <HowItWorks />
    </div>
  )
}