import { Link } from 'react-router'

export function Welcome() {
  return (
    <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200 md:p-10">
      <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">Is your invoice correct?</h1>
      <p className="mt-3 max-w-2xl text-base text-slate-600 md:text-lg">
        Upload the contract, the purchase order and the invoice. We read them, do the sums, and tell
        you if the vendor charged the right amount.
      </p>
      <Link
        to="/new"
        className="mt-6 inline-block rounded-lg bg-slate-900 px-6 py-3 text-base font-medium text-white hover:bg-slate-700"
      >
        Check an invoice
      </Link>
    </section>
  )
}