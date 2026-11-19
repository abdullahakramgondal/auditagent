import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router'
import { describe, expect, it } from 'vitest'
import { fetchMock, installFetchMock } from '@/test/fetchMock'
import { createWrapper } from '@/test/queryWrapper'
import { AuthForm } from './AuthForm'

installFetchMock()

type Route = { body: unknown; status?: number }

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

const NOBODY: Route = { body: { detail: 'Please log in.' }, status: 401 }

function setup(mode: 'login' | 'register') {
  render(
    <MemoryRouter initialEntries={['/start']}>
      <Routes>
        <Route path="/start" element={<AuthForm mode={mode} />} />
        <Route path="/" element={<p>home page</p>} />
      </Routes>
    </MemoryRouter>,
    { wrapper: createWrapper() },
  )
  return userEvent.setup()
}

async function fill(user: ReturnType<typeof setup>, button: string) {
  await user.type(await screen.findByLabelText('Email'), 'ali@example.com')
  await user.type(screen.getByLabelText('Password'), 'password123')
  await user.click(screen.getByRole('button', { name: button }))
}

describe('AuthForm', () => {
  it('logs in, sends the email and password, and opens the home page', async () => {
    serve({ '/auth/me': NOBODY, '/auth/login': { body: { email: 'ali@example.com' } } })
    const user = setup('login')
    await fill(user, 'Log in')
    expect(await screen.findByText('home page')).toBeInTheDocument()
    const call = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/auth/login'))
    expect(call?.[1]?.method).toBe('POST')
    expect(JSON.parse(String(call?.[1]?.body))).toEqual({
      email: 'ali@example.com',
      password: 'password123',
    })
    expect(call?.[1]?.credentials).toBe('include')
  })

  it('shows the reason when the password is wrong and stays on the form', async () => {
    serve({
      '/auth/me': NOBODY,
      '/auth/login': { body: { detail: 'Wrong email or password.' }, status: 401 },
    })
    const user = setup('login')
    await fill(user, 'Log in')
    expect(await screen.findByRole('alert')).toHaveTextContent('Wrong email or password.')
    expect(screen.queryByText('home page')).not.toBeInTheDocument()
  })

  it('creates an account and opens the home page', async () => {
    serve({ '/auth/me': NOBODY, '/auth/register': { body: { email: 'ali@example.com' } } })
    const user = setup('register')
    await fill(user, 'Create account')
    expect(await screen.findByText('home page')).toBeInTheDocument()
  })

  it('shows the reason when the email is already used', async () => {
    serve({
      '/auth/me': NOBODY,
      '/auth/register': {
        body: { detail: 'An account with this email already exists.' },
        status: 409,
      },
    })
    const user = setup('register')
    await fill(user, 'Create account')
    expect(await screen.findByRole('alert')).toHaveTextContent('already exists')
  })

  it('leads a person who is already logged in straight to the home page', async () => {
    serve({ '/auth/me': { body: { email: 'ali@example.com' } } })
    setup('login')
    expect(await screen.findByText('home page')).toBeInTheDocument()
  })
})