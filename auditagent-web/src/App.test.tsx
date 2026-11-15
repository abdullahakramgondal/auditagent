import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('App', () => {
  it('shows the page title and the synthetic-documents notice', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: /start a new audit/i })).toBeInTheDocument()
    expect(screen.getByRole('note')).toHaveTextContent(/synthetic or test documents only/i)
  })
})