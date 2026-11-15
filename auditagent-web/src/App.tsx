export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="sticky top-0 border-b bg-white px-4 py-3">
        <span className="font-semibold">AuditAgent AI</span>
      </header>
      <p role="note" className="bg-slate-100 px-4 py-2 text-sm text-slate-600">
        Synthetic or test documents only. Do not upload real contracts or invoices.
      </p>
      <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6">
        <h1 className="text-2xl font-semibold tracking-tight">Start a new audit</h1>
      </main>
    </div>
  )
}