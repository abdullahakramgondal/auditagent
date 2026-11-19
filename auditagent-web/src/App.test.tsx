import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import { summary } from '@/mocks/fixtures/summary'
import { fetchMock, installFetchMock } from '@/test/fetchMock'
import { createWrapper } from '@/test/queryWrapper'
import App from './App'

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

const LOGGED_IN: Route = { body: { email: 'abdullah@example.com' } }
const LOGGED_OUT: Route = { body: { detail: 'Please log in.' }, status: 401 }

function renderAt(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
    { wrapper: createWrapper() },
  )
}

describe('App when somebody is logged in', () => {
  it('opens the dashboard with the nav, the notice and the email of the person', async () => {
    serve({ '/auth/me': LOGGED_IN, '/audits/summary': { body: summary } })
    renderAt('/')
    expect(await screen.findByRole('heading', { name: /is your invoice correct/i })).toBeInTheDocument()
    expect(screen.getByRole('note')).toHaveTextContent(/synthetic or test documents only/i)
    expect(screen.getByRole('link', { name: 'Dashboard' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByText('abdullah@example.com')).toBeInTheDocument()
    expect(await screen.findByText('Invoices checked')).toBeInTheDocument()
  })

  it('opens the upload page at /new', async () => {
    serve({ '/auth/me': LOGGED_IN })
    renderAt('/new')
    expect(await screen.findByRole('heading', { name: /start a new audit/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'New audit' })).toHaveAttribute('aria-current', 'page')
  })

  it('opens the history page', async () => {
    serve({ '/auth/me': LOGGED_IN, '/audits': { body: [] } })
    renderAt('/history')
    expect(await screen.findByRole('heading', { name: /audit history/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'History' })).toHaveAttribute('aria-current', 'page')
    expect(await screen.findByText('No audits yet')).toBeInTheDocument()
  })

  it('shows a page not found for an unknown address, with a way back', async () => {
    serve({ '/auth/me': LOGGED_IN })
    renderAt('/nowhere')
    expect(await screen.findByRole('heading', { name: /page not found/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Go to the dashboard' })).toHaveAttribute('href', '/')
  })

  it('logs out and leads to the login page', async () => {
    serve({
      '/auth/me': LOGGED_IN,
      '/audits/summary': { body: summary },
      '/auth/logout': { body: { status: 'ok' } },
    })
    renderAt('/')
    await userEvent.setup().click(await screen.findByRole('button', { name: 'Log out' }))
    expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'History' })).not.toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(true)
  })
})

describe('App when nobody is logged in', () => {
  it('leads every private page to the login page', async () => {
    serve({ '/auth/me': LOGGED_OUT })
    renderAt('/history')
    expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'History' })).not.toBeInTheDocument()
  })

  it('opens the register page without a login', async () => {
    serve({ '/auth/me': LOGGED_OUT })
    renderAt('/register')
    expect(await screen.findByRole('heading', { name: 'Create an account' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Create account' })).toBeInTheDocument()
  })
})