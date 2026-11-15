import { NavLink, Outlet } from 'react-router'

function linkClass({ isActive }: { isActive: boolean }): string {
  return `rounded-md px-3 py-2 text-sm font-medium ${
    isActive ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'
  }`
}

export function AppShell() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:rounded-md focus:bg-white focus:px-3 focus:py-2"
      >
        Skip to content
      </a>
      <header className="sticky top-0 z-10 border-b bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-14 w-full max-w-5xl items-center justify-between px-4 sm:px-6">
          <span className="font-semibold">AuditAgent AI</span>
          <nav aria-label="Main" className="flex gap-1">
            <NavLink to="/" end className={linkClass}>
              New audit
            </NavLink>
            <NavLink to="/history" className={linkClass}>
              History
            </NavLink>
          </nav>
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