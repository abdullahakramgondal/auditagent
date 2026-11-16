import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import { SummarySchema } from '@/api/schemas'
import { summary } from '@/mocks/fixtures/summary'
import { fetchMock, installFetchMock, respondJson } from '@/test/fetchMock'
import { createWrapper } from '@/test/queryWrapper'
import { summaryRefetchInterval } from '../hooks/useAuditSummary'
import { HowItWorks } from './HowItWorks'
import { SummaryView } from './SummaryView'
import { Welcome } from './Welcome'

installFetchMock()

function renderIn(ui: React.ReactNode) {
  render(<MemoryRouter>{ui}</MemoryRouter>, { wrapper: createWrapper() })
}

function card(label: string): HTMLElement {
  const item = screen.getByText(label).closest('li')
  if (!item) throw new Error(`no card called ${label}`)
  return item
}

describe('Welcome', () => {
  it('asks the question and offers one clear button', () => {
    renderIn(<Welcome />)
    expect(screen.getByRole('heading', { name: 'Is your invoice correct?' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Check an invoice' })).toHaveAttribute('href', '/new')
  })
})

describe('HowItWorks', () => {
  it('explains the three steps in plain words', () => {
    renderIn(<HowItWorks />)
    expect(screen.getByText('Upload three PDFs')).toBeInTheDocument()
    expect(screen.getByText('Wait a minute or two')).toBeInTheDocument()
    expect(screen.getByText('Read the answer')).toBeInTheDocument()
  })
})

describe('SummaryView', () => {
  it('shows the counts and the money that the backend added', async () => {
    respondJson(summary)
    renderIn(<SummaryView />)
    await screen.findByText('Invoices checked')
    expect(within(card('Invoices checked')).getByText('5')).toBeInTheDocument()
    expect(within(card('Correct invoices')).getByText('1')).toBeInTheDocument()
    expect(within(card('Invoices with a mistake')).getByText('1')).toBeInTheDocument()
    expect(within(card('Need a person')).getByText('1')).toBeInTheDocument()
    expect(screen.getByText('PKR 1,041,250')).toBeInTheDocument()
    expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/audits/summary')
  })

  it('says how many audits are running and how many could not finish', async () => {
    respondJson(summary)
    renderIn(<SummaryView />)
    expect(await screen.findByText(/1 audit is still being checked/)).toBeInTheDocument()
    expect(screen.getByText(/1 audit could not finish/)).toBeInTheDocument()
  })

  it('shows an invitation and a link when nothing has been checked yet', async () => {
    respondJson({ ...summary, total: 0, in_progress: 0, failed: 0, compliant: 0, non_compliant: 0, needs_review: 0, total_difference: '0' })
    renderIn(<SummaryView />)
    expect(await screen.findByText('You have not checked any invoice yet')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Check your first invoice' })).toHaveAttribute('href', '/new')
  })

  it('shows a loading placeholder until the answer comes', () => {
    fetchMock.mockImplementation(() => new Promise(() => {}))
    renderIn(<SummaryView />)
    expect(screen.getByText('Loading your numbers…')).toBeInTheDocument()
  })

  it('shows the reason and a retry button when the numbers cannot be loaded', async () => {
    respondJson({ detail: 'boom' }, 500)
    renderIn(<SummaryView />)
    expect(await screen.findByRole('alert')).toHaveTextContent('boom')
    respondJson({ ...summary, in_progress: 0, failed: 0 })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('Invoices checked')).toBeInTheDocument()
  })
})

describe('summaryRefetchInterval', () => {
  it('polls only while an audit is being checked', () => {
    expect(summaryRefetchInterval(undefined)).toBe(false)
    expect(summaryRefetchInterval(SummarySchema.parse(summary))).toBe(5000)
    expect(summaryRefetchInterval(SummarySchema.parse({ ...summary, in_progress: 0 }))).toBe(false)
  })
})