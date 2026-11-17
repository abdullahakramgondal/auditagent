import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import { compliant } from '@/mocks/fixtures/compliant'
import { history } from '@/mocks/fixtures/history'
import { needsReview } from '@/mocks/fixtures/needs-review'
import { nonCompliant } from '@/mocks/fixtures/non-compliant'
import { fetchMock, installFetchMock } from '@/test/fetchMock'
import { createWrapper } from '@/test/queryWrapper'
import { AuditView } from './AuditView'

installFetchMock()

type Route = { body: unknown; status?: number }

/** Answers each backend address with its own prepared body. */
function serve(routes: Record<string, Route>) {
  fetchMock.mockImplementation((input) => {
    const path = String(input).replace('http://localhost:8000', '')
    const route = routes[path]
    if (!route) return Promise.resolve(new Response('{}', { status: 404 }))
    return Promise.resolve(
      new Response(JSON.stringify(route.body), {
        status: route.status ?? 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
  })
}

function renderView(id: string) {
  render(
    <MemoryRouter>
      <AuditView id={id} />
    </MemoryRouter>,
    { wrapper: createWrapper() },
  )
}

const NON_COMPLIANT_ID = '3f9c2a7e5b1d4c8a9e0f6b2d7a1c4e83'
const COMPLIANT_ID = 'b81e4d0c7a2f49d3a6c15e9f0b7d2a64'
const REVIEW_ID = 'c5d2f7a19e3b4086b4a7d1e8c0f93b25'
const RUNNING_ID = 'd90a1b6e3c7f4285a1e4b8d2f6c03a97'
const FAILED_ID = 'a47e0c9d2b185f3680d6e1a9c4f72b58'

describe('a job that is still working', () => {
  it('shows that the audit is running and no slow notice for a fresh job', async () => {
    const fresh = { ...history[0], created_at: new Date().toISOString() }
    serve({ [`/audits/${RUNNING_ID}`]: { body: fresh } })
    renderView(RUNNING_ID)
    expect(await screen.findByRole('heading', { name: 'Audit in progress' })).toBeInTheDocument()
    expect(screen.getByText(/reading the documents/i)).toBeInTheDocument()
    expect(screen.queryByText(/taking longer than usual/i)).not.toBeInTheDocument()
  })

  it('says that a queued job is waiting', async () => {
    const queued = { ...history[0], state: 'queued', created_at: new Date().toISOString() }
    serve({ [`/audits/${RUNNING_ID}`]: { body: queued } })
    renderView(RUNNING_ID)
    expect(await screen.findByText('Waiting to start…')).toBeInTheDocument()
  })

  it('tells the person to come back later when the job takes more than five minutes', async () => {
    serve({ [`/audits/${RUNNING_ID}`]: { body: history[0] } }) // created a day ago
    renderView(RUNNING_ID)
    expect(await screen.findByText(/taking longer than usual/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'History' })).toHaveAttribute('href', '/history')
  })
})

describe('a job that failed', () => {
  it('shows the busy-service text and a way to start again', async () => {
    serve({ [`/audits/${FAILED_ID}`]: { body: history[4] } })
    renderView(FAILED_ID)
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The language model service is busy. Try again in a few minutes.',
    )
    expect(screen.getByRole('link', { name: 'Start a new audit' })).toHaveAttribute('href', '/new')
  })

  it('shows the error text of a file that cannot be used', async () => {
    const badFile = {
      ...history[4],
      error_kind: 'bad_file',
      error: 'One of the files cannot be used: Not a PDF file',
    }
    serve({ [`/audits/${FAILED_ID}`]: { body: badFile } })
    renderView(FAILED_ID)
    expect(await screen.findByRole('alert')).toHaveTextContent('Not a PDF file')
  })
})

describe('a finished audit with mistakes', () => {
  function serveNonCompliant() {
    serve({
      [`/audits/${NON_COMPLIANT_ID}`]: { body: history[3] },
      [`/audits/${NON_COMPLIANT_ID}/result`]: { body: nonCompliant },
    })
  }

  it('shows the status label, the plain headline and the three money boxes', async () => {
    serveNonCompliant()
    renderView(NON_COMPLIANT_ID)
    expect(await screen.findByRole('heading', { name: 'Invoice check result' })).toBeInTheDocument()
    expect(screen.getByText('Non-compliant')).toBeInTheDocument()
    expect(screen.getByText('This invoice is too high')).toBeInTheDocument()
    expect(
      screen.getByText('Do not pay it as it is. Ask the vendor for a corrected invoice.'),
    ).toBeInTheDocument()
    expect(screen.getByText('The vendor is asking for')).toBeInTheDocument()
    expect(screen.getByText('The right amount is')).toBeInTheDocument()
    expect(screen.getAllByText('Overcharged by').length).toBeGreaterThan(0)
    expect(screen.getAllByText('PKR 3,421,250').length).toBeGreaterThan(0)
    expect(screen.getAllByText('PKR 1,041,250').length).toBeGreaterThan(0)
    expect(screen.getAllByText('PKR 4,462,500').length).toBeGreaterThan(0)
  })

  it('lists every problem with its explanation and the sentence of the contract', async () => {
    serveNonCompliant()
    renderView(NON_COMPLIANT_ID)
    expect(await screen.findByRole('heading', { name: 'What is wrong' })).toBeInTheDocument()
    expect(screen.getAllByRole('heading', { level: 3 })).toHaveLength(4)
    expect(screen.getByText(/The price per item is higher than agreed/)).toBeInTheDocument()
    expect(screen.getByText(/The delivery was late, but no penalty was taken off/)).toBeInTheDocument()
    expect(screen.getByText('PKR 531,250 too much')).toBeInTheDocument()
    expect(screen.getByText('A rule was broken')).toBeInTheDocument()
    expect(screen.getByText('This one does not change the amount to pay.')).toBeInTheDocument()
    expect(screen.getByText('The invoice does not show this discount.')).toBeInTheDocument()
    expect(screen.getByText(/which is 9 days late/)).toBeInTheDocument()
    expect(screen.getAllByText('What the contract says (page 6)')).toHaveLength(3)
    expect(screen.getByText('What the contract says (page 4)')).toBeInTheDocument()
    expect(
      screen.queryByRole('heading', { name: 'What a person should check' }),
    ).not.toBeInTheDocument()
  })

  it('shows the working-out line by line, written by the backend', async () => {
    serveNonCompliant()
    renderView(NON_COMPLIANT_ID)
    expect(await screen.findByRole('heading', { name: 'How we worked it out' })).toBeInTheDocument()
    expect(screen.getByText('What the vendor is asking for')).toBeInTheDocument()
    expect(screen.getByText('The same goods at the agreed price')).toBeInTheDocument()
    expect(screen.getByText('The right amount to pay')).toBeInTheDocument()
    expect(screen.getByText('− PKR 531,250')).toBeInTheDocument()
    expect(screen.getByText('− PKR 297,500')).toBeInTheDocument()
    expect(screen.getByText(/so 5 × 2.5% = 12.5%/)).toBeInTheDocument()
  })

  it('shows what was checked, with a word and not only a colour', async () => {
    serveNonCompliant()
    renderView(NON_COMPLIANT_ID)
    expect(await screen.findByRole('heading', { name: 'What we checked' })).toBeInTheDocument()
    expect(screen.getAllByText(/Problem found/)).toHaveLength(4)
    expect(screen.getByText(/Tax and extra charges are not checked/)).toBeInTheDocument()
  })

  it('moves the focus to the result heading', async () => {
    serveNonCompliant()
    renderView(NON_COMPLIANT_ID)
    const heading = await screen.findByRole('heading', { name: 'Invoice check result' })
    expect(heading).toHaveFocus()
  })

  it('links to the PDF report and the JSON download, and lists the documents that were read', async () => {
    serveNonCompliant()
    renderView(NON_COMPLIANT_ID)
    expect(await screen.findByRole('link', { name: 'Download PDF report' })).toHaveAttribute(
      'href',
      `http://localhost:8000/audits/${NON_COMPLIANT_ID}/report.pdf`,
    )
    expect(screen.getByRole('link', { name: 'Download JSON' })).toHaveAttribute(
      'href',
      `http://localhost:8000/audits/${NON_COMPLIANT_ID}/result.json`,
    )
    expect(screen.getByRole('heading', { name: 'The documents we read' })).toBeInTheDocument()
    expect(screen.getByText('Contract rules')).toBeInTheDocument()
    expect(screen.getByText('Purchase order')).toBeInTheDocument()
    expect(screen.getByText('Invoice')).toBeInTheDocument()
  })

  it('keeps the technical details in small print at the end', async () => {
    serveNonCompliant()
    renderView(NON_COMPLIANT_ID)
    expect(await screen.findByText(/Report number 3f9c2a7e/)).toBeInTheDocument()
  })
})

describe('a finished correct audit', () => {
  function serveCompliant() {
    serve({
      [`/audits/${COMPLIANT_ID}`]: { body: history[2] },
      [`/audits/${COMPLIANT_ID}/result`]: { body: compliant },
    })
  }

  it('says that no problem was found in the four things, and does not promise more', async () => {
    serveCompliant()
    renderView(COMPLIANT_ID)
    expect(await screen.findByText('No problems found')).toBeInTheDocument()
    expect(screen.getByText('Compliant')).toBeInTheDocument()
    expect(
      screen.getByText(/The 1 rule we found in the contract matches the invoice/),
    ).toBeInTheDocument()
    expect(screen.queryByText(/go ahead and pay/i)).not.toBeInTheDocument()
  })

  it('shows what was checked instead of a "What is wrong" box, and no overcharge card', async () => {
    serveCompliant()
    renderView(COMPLIANT_ID)
    expect(await screen.findByRole('heading', { name: 'What we checked' })).toBeInTheDocument()
    expect(screen.getByText('Delivered on time (14 October 2026).')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'What is wrong' })).not.toBeInTheDocument()
    expect(screen.queryByText('Overcharged by')).not.toBeInTheDocument()
    expect(screen.getByText('The right amount is')).toBeInTheDocument()
  })
})

describe('a finished audit that needs a person', () => {
  it('explains each open point in plain words, with what to do, and shows no amounts', async () => {
    serve({
      [`/audits/${REVIEW_ID}`]: { body: history[1] },
      [`/audits/${REVIEW_ID}/result`]: { body: needsReview },
    })
    renderView(REVIEW_ID)
    expect(await screen.findByText('We could not fully check this invoice')).toBeInTheDocument()
    expect(screen.getByText('Needs human review')).toBeInTheDocument()
    expect(screen.getByText('Please ask a person to look at it before you pay.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'What a person should check' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'About the invoice' })).toBeInTheDocument()
    expect(screen.getByText('We could not read the delivery date')).toBeInTheDocument()
    expect(screen.getAllByText(/What to do:/).length).toBe(2)
    expect(screen.getAllByText('Technical details')).toHaveLength(2)
    expect(screen.queryByText('The vendor is asking for')).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'What is wrong' })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'What we checked' })).toBeInTheDocument()
    expect(screen.getByText(/Could not check/)).toBeInTheDocument()
  })
})

describe('errors', () => {
  it('shows the reason when the audit is unknown', async () => {
    serve({ [`/audits/${NON_COMPLIANT_ID}`]: { body: { detail: 'Unknown audit.' }, status: 404 } })
    renderView(NON_COMPLIANT_ID)
    expect(await screen.findByRole('alert')).toHaveTextContent('Unknown audit.')
  })

  it('never shows a result that breaks the contract, and names the audit', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    serve({
      [`/audits/${NON_COMPLIANT_ID}`]: { body: history[3] },
      [`/audits/${NON_COMPLIANT_ID}/result`]: { body: { ...nonCompliant, status: 'MAYBE' } },
    })
    renderView(NON_COMPLIANT_ID)
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/unexpected response/i)
    expect(alert).toHaveTextContent(NON_COMPLIANT_ID)
    expect(screen.queryByRole('heading', { name: 'Invoice check result' })).not.toBeInTheDocument()
  })
})