import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { AuditResultSchema } from '@/api/schemas'
import { nonCompliant } from '@/mocks/fixtures/non-compliant'
import { FindingRow } from './FindingRow'

const finding = AuditResultSchema.parse(nonCompliant).findings[1] // late penalty, page 4

function setup() {
  render(
    <table>
      <tbody>
        <FindingRow finding={finding} />
      </tbody>
    </table>,
  )
  return userEvent.setup()
}

describe('FindingRow', () => {
  it('shows the clause and the difference, and keeps the details hidden', () => {
    setup()
    expect(screen.getByRole('rowheader', { name: 'Late delivery penalty' })).toBeInTheDocument()
    expect(screen.getAllByText('PKR 531,250')[0]).toBeInTheDocument()
    expect(screen.getByText(finding.source.text)).not.toBeVisible()
    const button = screen.getByRole('button', { name: 'Show clause for Late delivery penalty' })
    expect(button).toHaveAttribute('aria-expanded', 'false')
  })

  it('opens to the clause text, its page and the amounts, and closes again', async () => {
    const user = setup()
    await user.click(screen.getByRole('button', { name: 'Show clause for Late delivery penalty' }))
    expect(screen.getByText(finding.source.text)).toBeVisible()
    expect(screen.getByText('Contract, page 4')).toBeVisible()
    expect(screen.getByText('PKR 3,718,750')).toBeVisible()
    const hide = screen.getByRole('button', { name: 'Hide clause for Late delivery penalty' })
    expect(hide).toHaveAttribute('aria-expanded', 'true')
    await user.click(hide)
    expect(screen.getByText(finding.source.text)).not.toBeVisible()
  })

  it('shows a dash for an amount that the finding does not have', async () => {
    const payment = AuditResultSchema.parse(nonCompliant).findings[3] // payment terms: no amounts
    render(
      <table>
        <tbody>
          <FindingRow finding={payment} />
        </tbody>
      </table>,
    )
    expect(screen.getAllByText('—').length).toBe(2)
  })
})