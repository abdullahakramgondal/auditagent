import { Link } from 'react-router'

export function NotFoundPage() {
  return (
    <div className="flex flex-col gap-2">
      <h1 className="text-2xl font-semibold tracking-tight">Page not found</h1>
      <Link to="/" className="text-blue-700 underline">
        Start a new audit
      </Link>
    </div>
  )
}