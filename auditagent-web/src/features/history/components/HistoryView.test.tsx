import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import { history } from '@/mocks/fixtures/history'
import { fetchMock, installFetchMock, respondJson } from '@/test/fetchMock'
import { createWrapper } from '@/test/queryWrapper'
import { HistoryView } from './HistoryView'

installFetchMock()

function renderView() {
  render(
    <MemoryRouter>
      <HistoryView />
    </MemoryRouter>,
    { wrapper: createWrapper() },
  )
}

describe('HistoryView with audits', () => {
  it('shows one row for each audit under a header row', async () => {
    respondJson(history)
    renderView()
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(screen.getAllByRole('row')).toHaveLength(6)
  })

  it('shows the date as a link to the audit, in Pakistan time', async () => {
    respondJson(history)
    renderView()
    const link = await screen.findByRole('link', { name: '14 Nov 2026, 14:41' })
    expect(link).toHaveAttribute('href', '/audits/3f9c2a7e5b1d4c8a9e0f6b2d7a1c4e83')
    expect(screen.getByRole('link', { name: '13 Nov 2026, 23:12' })).toHaveAttribute(
      'href',
      '/audits/a47e0c9d2b185f3680d6e1a9c4f72b58',
    )
  })

  it('shows every kind of row with its text, not only a colour', async () => {
    respondJson(history)
    renderView()
    await screen.findByRole('table')
    expect(screen.getByText('Running')).toBeInTheDocument()
    expect(screen.getByText('Needs human review')).toBeInTheDocument()
    expect(screen.getByText('Compliant')).toBeInTheDocument()
    expect(screen.getByText('Non-compliant')).toBeInTheDocument()
    expect(screen.getByText('Failed')).toBeInTheDocument()
  })

  it('shows the difference of a finished audit and the model that made it', async () => {
    respondJson(history)
    renderView()
    await screen.findByRole('table')
    expect(screen.getByText('PKR 1,041,250')).toBeInTheDocument()
    expect(screen.getByText('PKR 0')).toBeInTheDocument()
    expect(screen.getAllByText('gemini-3.1-flash-lite')).toHaveLength(2)
    expect(screen.getByText('qwen2.5:7b')).toBeInTheDocument()
  })
})

describe('HistoryView without audits', () => {
  it('shows an empty state with a link to the upload screen', async () => {
    respondJson([])
    renderView()
    expect(await screen.findByText('No audits yet')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Start a new audit' })).toHaveAttribute('href', '/')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })
})

describe('HistoryView while loading', () => {
  it('shows a loading placeholder until the answer comes', () => {
    fetchMock.mockImplementation(() => new Promise(() => {}))
    renderView()
    expect(screen.getByText('Loading history…')).toBeInTheDocument()
  })
})

describe('HistoryView errors', () => {
  it('shows the reason and a retry button that loads the list again', async () => {
    respondJson({ detail: 'boom' }, 500)
    renderView()
    expect(await screen.findByRole('alert')).toHaveTextContent('boom')

    respondJson([])
    await userEvent.setup().click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('No audits yet')).toBeInTheDocument()
  })

  it('never shows rows that break the contract', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    respondJson([{ ...history[0], state: 'paused' }])
    renderView()
    expect(await screen.findByRole('alert')).toHaveTextContent(/unexpected response/i)
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })
})