import { describe, expect, it } from 'vitest'
import { compliant } from '@/mocks/fixtures/compliant'
import { needsReview } from '@/mocks/fixtures/needs-review'
import { nonCompliant } from '@/mocks/fixtures/non-compliant'
import { AuditResultSchema } from './schemas'

function clone(value: unknown): Record<string, unknown> {
  return JSON.parse(JSON.stringify(value)) as Record<string, unknown>
}

describe('the plain summary of a result', () => {
  it('has one problem for each finding, in the same order', () => {
    const result = AuditResultSchema.parse(nonCompliant)
    expect(result.plain.headline).toBe('This invoice is too high')
    expect(result.plain.problems.map((p) => p.clause_type)).toEqual(
      result.findings.map((f) => f.clause_type),
    )
  })

  it('has no problems for a correct invoice and for one that needs a person', () => {
    expect(AuditResultSchema.parse(compliant).plain.problems).toEqual([])
    expect(AuditResultSchema.parse(needsReview).plain.problems).toEqual([])
  })

  it('is required: a result without it is refused', () => {
    const broken = clone(nonCompliant)
    delete broken.plain
    expect(AuditResultSchema.safeParse(broken).success).toBe(false)
  })

  it('refuses a problem that has no sentence of the contract', () => {
    const broken = clone(nonCompliant) as { plain: { problems: Record<string, unknown>[] } }
    delete broken.plain.problems[0].quote
    expect(AuditResultSchema.safeParse(broken).success).toBe(false)
  })
})