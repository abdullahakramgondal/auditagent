import { describe, expect, it } from 'vitest'
import { AuditResultSchema } from '@/api/schemas'
import { nonCompliant } from '@/mocks/fixtures/non-compliant'
import { bannerMessage } from './bannerMessage'
import { clauseLabels, fieldLabel } from './clauseLabels'
import { SLOW_AFTER_MS, elapsedMs, formatElapsed, isSlow } from './elapsed'
import { groupReviewReasons } from './groupReviewReasons'
import { ruleSummary } from './ruleSummary'

describe('bannerMessage', () => {
  it('says that a compliant invoice matches the contract', () => {
    expect(bannerMessage('COMPLIANT', '0.00')).toBe('The invoice matches the contract.')
  })

  it('names the amount of a non-compliant invoice', () => {
    expect(bannerMessage('NON_COMPLIANT', '1041250.00')).toBe(
      'The invoice is PKR 1,041,250 above what the contract allows.',
    )
  })

  it('does not name an amount when the breach has none', () => {
    const text = 'The invoice breaks a contract rule that has no amount, for example the payment terms.'
    expect(bannerMessage('NON_COMPLIANT', '0')).toBe(text)
    expect(bannerMessage('NON_COMPLIANT', '0.00')).toBe(text)
    expect(bannerMessage('NON_COMPLIANT', null)).toBe(text)
  })

  it('asks for a human look when something could not be proven', () => {
    expect(bannerMessage('NEEDS_REVIEW', null)).toContain('could not be proven')
  })
})

describe('clauseLabels', () => {
  it('has the words of the screen for every clause type', () => {
    expect(clauseLabels).toEqual({
      late_penalty: 'Late delivery penalty',
      volume_discount: 'Volume discount',
      payment_terms: 'Payment terms',
      unit_price: 'Agreed unit price',
    })
  })

  it('writes a field name as a label', () => {
    expect(fieldLabel('delivery_date')).toBe('Delivery date')
    expect(fieldLabel('late_penalty')).toBe('Late delivery penalty')
    expect(fieldLabel('')).toBe('')
  })
})

describe('groupReviewReasons', () => {
  it('groups by document in a fixed order and leaves out an empty group', () => {
    const groups = groupReviewReasons([
      { source: 'audit', field: '', reason: 'a' },
      { source: 'invoice', field: 'delivery_date', reason: 'b' },
      { source: 'contract', field: 'late_penalty', reason: 'c' },
      { source: 'invoice', field: 'due_date', reason: 'd' },
    ])
    expect(groups.map((g) => g.label)).toEqual(['Contract', 'Invoice', 'Audit'])
    expect(groups[1].reasons.map((r) => r.reason)).toEqual(['b', 'd'])
  })

  it('gives nothing for no reasons', () => {
    expect(groupReviewReasons([])).toEqual([])
  })
})

describe('elapsed time', () => {
  const start = '2026-11-14T10:00:00Z'
  const at = (iso: string) => Date.parse(iso)

  it('counts from the creation time of the job', () => {
    expect(elapsedMs(start, at('2026-11-14T10:01:30Z'))).toBe(90000)
  })

  it('never goes below zero and ignores a time that cannot be read', () => {
    expect(elapsedMs(start, at('2026-11-14T09:00:00Z'))).toBe(0)
    expect(elapsedMs('not a time', Date.now())).toBe(0)
  })

  it('is slow only after five minutes', () => {
    const exactly = at(start) + SLOW_AFTER_MS
    expect(isSlow(start, exactly)).toBe(false)
    expect(isSlow(start, exactly + 1)).toBe(true)
  })

  it('writes seconds and minutes', () => {
    expect(formatElapsed(0)).toBe('0 s')
    expect(formatElapsed(45000)).toBe('45 s')
    expect(formatElapsed(125000)).toBe('2 min 05 s')
  })
})

describe('ruleSummary', () => {
  const rules = AuditResultSchema.parse(nonCompliant).contract.rules

  it('writes a per-day penalty with its cap and grace days', () => {
    expect(ruleSummary(rules[0])).toBe(
      '2.5% per day after 28 February 2027, up to 15%, first 4 days free',
    )
  })

  it('writes a flat penalty without a cap', () => {
    const flat = { ...rules[0], mode: 'flat_percent' as const, percent: '10', cap_percent: null, grace_days: 0 }
    expect(ruleSummary(flat)).toBe('10% once if delivery is after 28 February 2027')
  })

  it('writes the other three kinds of rule', () => {
    expect(ruleSummary(rules[1])).toBe('7% discount from 30 units')
    expect(ruleSummary(rules[2])).toBe('Dell UltraSharp U2723QE Monitor at PKR 85,000 per unit')
    expect(ruleSummary(rules[3])).toBe('Net 28 days from the invoice date')
  })
})