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
    expect(screen.getByRole('link', { name: 'Start a new audit' })).toHaveAttribute('href', '/')
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

describe('a finished non-compliant audit', () => {
  function serveNonCompliant() {
    serve({
      [`/audits/${NON_COMPLIANT_ID}`]: { body: history[3] },
      [`/audits/${NON_COMPLIANT_ID}/result`]: { body: nonCompliant },
    })
  }

  it('shows the banner, the money and the four findings', async () => {
    serveNonCompliant()
    renderView(NON_COMPLIANT_ID)
    expect(await screen.findByRole('heading', { name: 'Audit result' })).toBeInTheDocument()
    expect(screen.getByText('Non-compliant')).toBeInTheDocument()
    expect(
      screen.getByText('The invoice is PKR 1,041,250 above what the contract allows.'),
    ).toBeInTheDocument()
    expect(screen.getByText('PKR 3,421,250')).toBeInTheDocument()
    expect(screen.getByText('PKR 1,041,250')).toBeInTheDocument()
    expect(screen.getAllByText('PKR 4,462,500').length).toBeGreaterThan(0)
    expect(screen.getByRole('heading', { name: 'Findings (4)' })).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /show clause for/i })).toHaveLength(4)
    expect(screen.queryByRole('heading', { name: 'Reasons to check' })).not.toBeInTheDocument()
  })

  it('moves the focus to the result heading', async () => {
    serveNonCompliant()
    renderView(NON_COMPLIANT_ID)
    const heading = await screen.findByRole('heading', { name: 'Audit result' })
    expect(heading).toHaveFocus()
  })

  it('links to the JSON download and lists the documents that were read', async () => {
    serveNonCompliant()
    renderView(NON_COMPLIANT_ID)
    const link = await screen.findByRole('link', { name: 'Download JSON' })
    expect(link).toHaveAttribute(
      'href',
      `http://localhost:8000/audits/${NON_COMPLIANT_ID}/result.json`,
    )
    expect(screen.getByRole('link', { name: 'Download PDF report' })).toHaveAttribute(
      'href',
      `http://localhost:8000/audits/${NON_COMPLIANT_ID}/report.pdf`,
    )
    expect(screen.getByText('Contract rules')).toBeInTheDocument()
    expect(screen.getByText('Purchase order')).toBeInTheDocument()
    expect(screen.getByText('Invoice')).toBeInTheDocument()
  })
})

describe('a finished compliant audit', () => {
  it('shows the green banner and says that nothing was found', async () => {
    serve({
      [`/audits/${COMPLIANT_ID}`]: { body: history[2] },
      [`/audits/${COMPLIANT_ID}/result`]: { body: compliant },
    })
    renderView(COMPLIANT_ID)
    expect(await screen.findByText('Compliant')).toBeInTheDocument()
    expect(screen.getByText('The invoice matches the contract.')).toBeInTheDocument()
    expect(screen.getByText('No billing differences found.')).toBeInTheDocument()
  })
})

describe('a finished audit that needs review', () => {
  it('shows the amber banner, the reasons and no amounts', async () => {
    serve({
      [`/audits/${REVIEW_ID}`]: { body: history[1] },
      [`/audits/${REVIEW_ID}/result`]: { body: needsReview },
    })
    renderView(REVIEW_ID)
    expect(await screen.findByText('Needs human review')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Reasons to check' })).toBeInTheDocument()
    expect(screen.getByText(/the document shows a date next to a label/i)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Invoice' })).toBeInTheDocument()
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(3)
    expect(screen.getByText('No billing differences found.')).toBeInTheDocument()
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
    expect(screen.queryByRole('heading', { name: 'Audit result' })).not.toBeInTheDocument()
  })
})