const STEPS = [
  {
    title: 'Upload three PDFs',
    text: 'The contract, the purchase order and the invoice of one purchase.',
  },
  {
    title: 'Wait a minute or two',
    text: 'The system reads the documents and does the sums. You can leave and come back later.',
  },
  {
    title: 'Read the answer',
    text: 'You get a clear result and a PDF report that you can keep or send to someone.',
  },
]

export function HowItWorks() {
  return (
    <section aria-labelledby="how-heading" className="flex flex-col gap-4">
      <h2 id="how-heading" className="text-lg font-semibold">
        How it works
      </h2>
      <ol className="grid gap-4 md:grid-cols-3">
        {STEPS.map((step, index) => (
          <li key={step.title} className="flex gap-4 rounded-xl bg-white p-5 ring-1 ring-slate-200">
            <span
              aria-hidden="true"
              className="flex size-9 shrink-0 items-center justify-center rounded-full bg-slate-900 font-semibold text-white"
            >
              {index + 1}
            </span>
            <div>
              <p className="font-semibold">{step.title}</p>
              <p className="mt-1 text-sm text-slate-600">{step.text}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}