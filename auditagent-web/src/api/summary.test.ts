import { describe, expect, it } from 'vitest'
import { summary } from '@/mocks/fixtures/summary'
import { fetchMock, installFetchMock, respondJson } from '@/test/fetchMock'
import { getSummary } from './audits'
import { SummarySchema } from './schemas'

installFetchMock()

describe('getSummary', () => {
  it('reads the numbers of the dashboard', async () => {
    respondJson(summary)
    const result = await getSummary()
    expect(result.total).toBe(5)
    expect(result.total_difference).toBe('1041250.00')
    expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/audits/summary')
  })
})

describe('SummarySchema', () => {
  it('keeps the money as text', () => {
    expect(typeof SummarySchema.parse(summary).total_difference).toBe('string')
  })

  it('refuses money that is a number, and a count that is text', () => {
    expect(SummarySchema.safeParse({ ...summary, total_difference: 1041250 }).success).toBe(false)
    expect(SummarySchema.safeParse({ ...summary, total: '5' }).success).toBe(false)
  })
})