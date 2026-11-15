import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { HistorySchema } from '@/api/schemas'
import { history } from '@/mocks/fixtures/history'
import { installFetchMock, respondJson } from '@/test/fetchMock'
import { createWrapper } from '@/test/queryWrapper'
import { historyRefetchInterval, useAuditHistory } from './useAuditHistory'

installFetchMock()

describe('historyRefetchInterval', () => {
  it('does not poll before there is any data', () => {
    expect(historyRefetchInterval(undefined)).toBe(false)
  })

  it('polls while one audit is still running', () => {
    expect(historyRefetchInterval(HistorySchema.parse(history))).toBe(5000)
  })

  it('stops when every audit is finished', () => {
    expect(historyRefetchInterval(HistorySchema.parse(history.slice(1)))).toBe(false)
  })
})

describe('useAuditHistory', () => {
  it('loads the history', async () => {
    respondJson(history.slice(1)) // no running audit: no polling in the test
    const { result } = renderHook(() => useAuditHistory(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toHaveLength(4)
    expect(result.current.data?.[0].status).toBe('NEEDS_REVIEW')
  })
})