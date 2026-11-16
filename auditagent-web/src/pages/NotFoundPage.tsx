import { Link } from 'react-router'

export function NotFoundPage() {
  return (
    <div className="flex flex-col gap-2">
      <h1 className="text-2xl font-semibold tracking-tight">Page not found</h1>
      <p className="text-sm text-slate-600">This address does not exist.</p>
      <Link to="/" className="text-blue-700 underline">
        Go to the dashboard
      </Link>
    </div>
  )
}