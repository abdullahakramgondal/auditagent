import type { CheckItem } from '@/api/types'

type Look = { text: string; tone: string; path: string }

// Icon and words together: colour is never the only signal.
const LOOK: Record<CheckItem['state'], Look> = {
  ok: {
    text: 'Checked, no problem',
    tone: 'text-green-800',
    path: 'M10 18a8 8 0 100-16 8 8 0 000 16zm3.7-9.3a1 1 0 00-1.4-1.4L9 10.6 7.7 9.3a1 1 0 00-1.4 1.4l2 2a1 1 0 001.4 0l4-4z',
  },
  problem: {
    text: 'Problem found',
    tone: 'text-red-800',
    path: 'M10 18a8 8 0 100-16 8 8 0 000 16zM8.7 7.3a1 1 0 00-1.4 1.4L8.6 10l-1.3 1.3a1 1 0 101.4 1.4L10 11.4l1.3 1.3a1 1 0 001.4-1.4L11.4 10l1.3-1.3a1 1 0 00-1.4-1.4L10 8.6 8.7 7.3z',
  },
  unchecked: {
    text: 'Could not check',
    tone: 'text-amber-900',
    path: 'M8.5 3.6a1.7 1.7 0 012.9 0l5.6 9.7A1.7 1.7 0 0115.6 16H4.4a1.7 1.7 0 01-1.5-2.7l5.6-9.7zM10 7a1 1 0 00-1 1v3a1 1 0 102 0V8a1 1 0 00-1-1zm0 7.5a1 1 0 100-2 1 1 0 000 2z',
  },
  none: {
    text: 'No rule found',
    tone: 'text-slate-600',
    path: 'M10 18a8 8 0 100-16 8 8 0 000 16zM6 10a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1z',
  },
}

/** The four things that the system checks, and how each one went. */
export function Checklist({ items }: { items: CheckItem[] }) {
  if (items.length === 0) return null
  return (
    <section aria-labelledby="checks-heading" className="flex flex-col gap-3">
      <h2 id="checks-heading" className="text-lg font-semibold">
        What we checked
      </h2>
      <p className="text-sm text-slate-600">
        We check four things: the price, the volume discount, the delivery date and the payment
        deadline. Tax and extra charges are not checked.
      </p>
      <ul className="rounded-xl bg-white ring-1 ring-slate-200">
        {items.map((item) => {
          const look = LOOK[item.state]
          return (
            <li
              key={item.clause_type}
              className="flex items-start gap-3 border-b border-slate-200 p-4 last:border-b-0"
            >
              <svg
                aria-hidden="true"
                viewBox="0 0 20 20"
                fill="currentColor"
                className={`mt-0.5 size-5 shrink-0 ${look.tone}`}
              >
                <path fillRule="evenodd" clipRule="evenodd" d={look.path} />
              </svg>
              <div>
                <p className="font-medium">
                  {item.label} <span className={`text-sm font-semibold ${look.tone}`}>· {look.text}</span>
                </p>
                <p className="text-sm text-slate-600">{item.detail}</p>
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}