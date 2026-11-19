import { Link, NavLink, Outlet } from 'react-router'
import { LogoutButton, useMe } from '@/features/auth'

function linkClass({ isActive }: { isActive: boolean }): string {
  return `inline-flex min-h-11 items-center rounded-md px-3 text-sm font-medium ${
    isActive ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'
  }`
}

/** The logo: a dark square with a tick, the same picture as the browser tab icon. */
function Logo() {
  return (
    <Link to="/" className="flex shrink-0 items-center gap-2 font-semibold">
      <svg aria-hidden="true" viewBox="0 0 32 32" className="size-7">
        <rect width="32" height="32" rx="7" fill="#0f172a" />
        <path
          d="M9 16.5l4.5 4.5L23 11"
          fill="none"
          stroke="#ffffff"
          strokeWidth="3.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      AuditAgent AI
    </Link>
  )
}

export function AppShell() {
  const me = useMe()
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:rounded-md focus:bg-white focus:px-3 focus:py-2"
      >
        Skip to content
      </a>
      <header className="sticky top-0 z-10 border-b bg-white/95 backdrop-blur">
        <div className="mx-auto flex min-h-14 w-full max-w-5xl flex-wrap items-center justify-between gap-x-4 gap-y-1 px-4 py-1 sm:px-6">
          <Logo />
          {me.data && (
            <div className="flex flex-wrap items-center gap-1">
              <nav aria-label="Main" className="flex flex-wrap gap-1">
                <NavLink to="/" end className={linkClass}>
                  Dashboard
                </NavLink>
                <NavLink to="/new" className={linkClass}>
                  New audit
                </NavLink>
                <NavLink to="/history" className={linkClass}>
                  History
                </NavLink>
              </nav>
              <span className="hidden max-w-48 truncate px-2 text-sm text-slate-600 md:inline">
                {me.data.email}
              </span>
              <LogoutButton />
            </div>
          )}
        </div>
      </header>
      <p role="note" className="bg-slate-100 px-4 py-2 text-sm text-slate-600 sm:px-6">
        Synthetic or test documents only. Do not upload real contracts or invoices.
      </p>
      <main id="main" className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6">
        <Outlet />
      </main>
    </div>
  )
}