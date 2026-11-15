import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router'
import { describe, expect, it } from 'vitest'
import { fetchMock, installFetchMock, respondJson } from '@/test/fetchMock'
import { createWrapper } from '@/test/queryWrapper'
import { UploadForm } from './UploadForm'

installFetchMock()

function pdf(name: string): File {
  return new File([`%PDF-1.4 ${name}`], name, { type: 'application/pdf' })
}

function setup() {
  render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={<UploadForm />} />
        <Route path="/audits/:id" element={<p>audit page</p>} />
      </Routes>
    </MemoryRouter>,
    { wrapper: createWrapper() },
  )
  return userEvent.setup({ applyAccept: false })
}

async function fillAll(user: ReturnType<typeof setup>) {
  await user.upload(screen.getByLabelText('Contract'), pdf('contract.pdf'))
  await user.upload(screen.getByLabelText('Purchase order'), pdf('po.pdf'))
  await user.upload(screen.getByLabelText('Invoice'), pdf('invoice.pdf'))
  await screen.findByText('invoice.pdf')
}

describe('UploadForm', () => {
  it('cannot start an audit before all three files are chosen', async () => {
    const user = setup()
    const button = screen.getByRole('button', { name: /start audit/i })
    expect(button).toBeDisabled()
    await user.upload(screen.getByLabelText('Contract'), pdf('contract.pdf'))
    await screen.findByText('contract.pdf')
    expect(button).toBeDisabled()
  })

  it('starts the audit with the three files and opens the audit page', async () => {
    respondJson({ audit_id: 'abc123' }, 202)
    const user = setup()
    await fillAll(user)
    const button = screen.getByRole('button', { name: /start audit/i })
    await waitFor(() => expect(button).toBeEnabled())
    await user.click(button)
    expect(await screen.findByText('audit page')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][1]?.method).toBe('POST')
  })

  it('refuses a file that is not a PDF and keeps the button disabled', async () => {
    const user = setup()
    const fake = new File(['hello world'], 'fake.pdf', { type: 'application/pdf' })
    await user.upload(screen.getByLabelText('Contract'), fake)
    expect(await screen.findByRole('alert')).toHaveTextContent('This is not a PDF file.')
    expect(screen.queryByText('fake.pdf')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /start audit/i })).toBeDisabled()
  })

  it('refuses the same file in two places', async () => {
    const user = setup()
    const file = pdf('contract.pdf')
    await user.upload(screen.getByLabelText('Contract'), file)
    await screen.findByText('contract.pdf')
    await user.upload(screen.getByLabelText('Invoice'), file)
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'This is the same file as the contract.',
    )
  })

  it('removes a chosen file', async () => {
    const user = setup()
    await user.upload(screen.getByLabelText('Contract'), pdf('contract.pdf'))
    await screen.findByText('contract.pdf')
    await user.click(screen.getByRole('button', { name: 'Remove contract file' }))
    expect(screen.queryByText('contract.pdf')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Choose contract file' })).toBeInTheDocument()
  })

  it('shows the reason when the backend refuses the files and keeps them', async () => {
    respondJson({ detail: 'The invoice file is not a PDF.' }, 400)
    const user = setup()
    await fillAll(user)
    const button = screen.getByRole('button', { name: /start audit/i })
    await waitFor(() => expect(button).toBeEnabled())
    await user.click(button)
    expect(await screen.findByText('The invoice file is not a PDF.')).toBeInTheDocument()
    expect(screen.getByText('invoice.pdf')).toBeInTheDocument()
    expect(screen.queryByText('audit page')).not.toBeInTheDocument()
  })
})