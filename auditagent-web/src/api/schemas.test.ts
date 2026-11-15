import Decimal from 'decimal.js'
import { describe, expect, it } from 'vitest'
import { z } from 'zod'
import { compliant } from '@/mocks/fixtures/compliant'
import { history } from '@/mocks/fixtures/history'
import { needsReview } from '@/mocks/fixtures/needs-review'
import { nonCompliant } from '@/mocks/fixtures/non-compliant'
import { AuditResultSchema, HistorySchema, JobInfoSchema, SubmittedSchema } from './schemas'

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

function expectValid(schema: z.ZodType, value: unknown) {
  const result = schema.safeParse(value)
  expect(result.success, result.success ? '' : z.prettifyError(result.error)).toBe(true)
}

function expectInvalid(schema: z.ZodType, value: unknown) {
  expect(schema.safeParse(value).success).toBe(false)
}

describe('AuditResultSchema with the three fixtures', () => {
  it('reads the non-compliant result', () => expectValid(AuditResultSchema, nonCompliant))
  it('reads the compliant result', () => expectValid(AuditResultSchema, compliant))
  it('reads the needs-review result', () => expectValid(AuditResultSchema, needsReview))

  it('keeps money as text and the page as a number', () => {
    const result = AuditResultSchema.parse(nonCompliant)
    expect(result.billed_total).toBe('4462500.00')
    expect(typeof result.findings[0].difference).toBe('string')
    expect(result.findings[0].source.page).toBe(6)
  })

  it('reads all four kinds of rule of the contract', () => {
    const result = AuditResultSchema.parse(nonCompliant)
    expect(result.contract.rules.map((rule) => rule.clause_type)).toEqual([
      'late_penalty',
      'volume_discount',
      'unit_price',
      'payment_terms',
    ])
  })

  it('has no amounts and no invoice in the needs-review result', () => {
    const result = AuditResultSchema.parse(needsReview)
    expect(result.billed_total).toBeNull()
    expect(result.invoice).toBeNull()
    expect(result.review_reasons).toHaveLength(2)
  })

  it('accepts amounts that are marked provisional next to review reasons', () => {
    const provisional = {
      ...nonCompliant,
      amounts_provisional: true,
      review_reasons: [{ source: 'contract', field: 'late_penalty', reason: 'a rule was refused' }],
    }
    expectValid(AuditResultSchema, provisional)
  })
})

describe('the fixtures add up (guards the numbers written by hand)', () => {
  it('the findings add up to the total, and billed minus correct is the total', () => {
    const result = AuditResultSchema.parse(nonCompliant)
    const sum = result.findings.reduce((acc, f) => acc.plus(f.difference), new Decimal(0))
    expect(sum.equals(result.total_difference ?? '0')).toBe(true)
    const gap = new Decimal(result.billed_total ?? '0').minus(result.correct_payable ?? '0')
    expect(gap.equals(result.total_difference ?? '0')).toBe(true)
  })
})

describe('AuditResultSchema refuses a broken contract', () => {
  it('refuses a finding without its clause source', () => {
    const broken = clone(nonCompliant) as { findings: { source?: unknown }[] }
    delete broken.findings[0].source
    expectInvalid(AuditResultSchema, broken)
  })

  it('refuses money that is a number and not a string', () => {
    expectInvalid(AuditResultSchema, { ...nonCompliant, billed_total: 4462500 })
  })

  it('refuses a status that the backend does not have', () => {
    expectInvalid(AuditResultSchema, { ...nonCompliant, status: 'MAYBE' })
  })

  it('refuses a rule of a kind that the backend does not have', () => {
    const broken = clone(nonCompliant) as { contract: { rules: { clause_type: string }[] } }
    broken.contract.rules[0].clause_type = 'warranty'
    expectInvalid(AuditResultSchema, broken)
  })

  it('refuses a date that is not year-month-day', () => {
    const broken = clone(nonCompliant) as { invoice: { delivery_date: string } }
    broken.invoice.delivery_date = '9 March 2027'
    expectInvalid(AuditResultSchema, broken)
  })

  it('refuses a result with a field missing', () => {
    const withoutFindings: Record<string, unknown> = { ...nonCompliant }
    delete withoutFindings.findings
    expectInvalid(AuditResultSchema, withoutFindings)
  })

  it('ignores a field that it does not know, and drops it', () => {
    const result = AuditResultSchema.parse({ ...nonCompliant, brand_new_field: 1 })
    expect('brand_new_field' in result).toBe(false)
  })
})

describe('JobInfoSchema and HistorySchema', () => {
  it('reads every row of the history fixture', () => expectValid(HistorySchema, history))

  it('reads a running job, a failed job and a finished job', () => {
    const states = HistorySchema.parse(history).map((row) => row.state)
    expect(states).toEqual(['running', 'done', 'done', 'done', 'failed'])
  })

  it('keeps the kind of error of a failed job', () => {
    const failed = JobInfoSchema.parse(history[4])
    expect(failed.error_kind).toBe('provider_unavailable')
    expect(failed.error).toContain('busy')
  })

  it('reads a time with a time zone offset', () => {
    expectValid(JobInfoSchema, { ...history[0], created_at: '2026-11-14T15:31:02+05:00' })
  })

  it('refuses a state that the backend does not have', () => {
    expectInvalid(JobInfoSchema, { ...history[0], state: 'paused' })
  })

  it('refuses a time that has no time zone', () => {
    expectInvalid(JobInfoSchema, { ...history[0], created_at: '2026-11-14 10:31:02' })
  })
})

describe('SubmittedSchema', () => {
  it('reads the answer of POST /audits', () => {
    expect(SubmittedSchema.parse({ audit_id: 'abc' }).audit_id).toBe('abc')
  })

  it('refuses an answer without an audit id', () => expectInvalid(SubmittedSchema, {}))
})