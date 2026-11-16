import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import { summary } from '@/mocks/fixtures/summary'
import { installFetchMock, respondJson } from '@/test/fetchMock'
import { createWrapper } from '@/test/queryWrapper'
import App from './App'

installFetchMock()

function renderAt(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
    { wrapper: createWrapper() },
  )
}

describe('App', () => {
  it('opens the dashboard at the start address, with the nav and the notice', async () => {
    respondJson(summary)
    renderAt('/')
    expect(screen.getByRole('heading', { name: /is your invoice correct/i })).toBeInTheDocument()
    expect(screen.getByRole('note')).toHaveTextContent(/synthetic or test documents only/i)
    expect(screen.getByRole('link', { name: 'Dashboard' })).toHaveAttribute('aria-current', 'page')
    expect(await screen.findByText('Invoices checked')).toBeInTheDocument()
  })

  it('opens the upload page at /new', () => {
    renderAt('/new')
    expect(screen.getByRole('heading', { name: /start a new audit/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'New audit' })).toHaveAttribute('aria-current', 'page')
  })

  it('opens the history page', async () => {
    respondJson([])
    renderAt('/history')
    expect(screen.getByRole('heading', { name: /audit history/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'History' })).toHaveAttribute('aria-current', 'page')
    expect(await screen.findByText('No audits yet')).toBeInTheDocument()
  })

  it('shows a page not found for an unknown address, with a way back', () => {
    renderAt('/nowhere')
    expect(screen.getByRole('heading', { name: /page not found/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Go to the dashboard' })).toHaveAttribute('href', '/')
  })
})