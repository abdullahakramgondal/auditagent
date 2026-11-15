import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import { createWrapper } from '@/test/queryWrapper'
import App from './App'

function renderAt(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
    { wrapper: createWrapper() },
  )
}

describe('App', () => {
  it('shows the upload page, the nav and the synthetic-documents notice', () => {
    renderAt('/')
    expect(screen.getByRole('heading', { name: /start a new audit/i })).toBeInTheDocument()
    expect(screen.getByRole('note')).toHaveTextContent(/synthetic or test documents only/i)
    expect(screen.getByRole('link', { name: 'New audit' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'History' })).toBeInTheDocument()
  })

  it('opens the history page', () => {
    renderAt('/history')
    expect(screen.getByRole('heading', { name: /audit history/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'History' })).toHaveAttribute('aria-current', 'page')
  })

  it('shows a page not found for an unknown address', () => {
    renderAt('/nowhere')
    expect(screen.getByRole('heading', { name: /page not found/i })).toBeInTheDocument()
  })
})