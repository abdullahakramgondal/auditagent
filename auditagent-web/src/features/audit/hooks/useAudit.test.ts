import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/api/client'
import { compliant } from '@/mocks/fixtures/compliant'
import { history } from '@/mocks/fixtures/history'
import { fetchMock, installFetchMock, respondJson } from '@/test/fetchMock'
import { createWrapper } from '@/test/queryWrapper'
import { auditRefetchInterval, useAudit } from './useAudit'
import { useAuditResult } from './useAuditResult'

installFetchMock()

describe('auditRefetchInterval', () => {
  it('keeps polling while the job has not finished', () => {
    expect(auditRefetchInterval(undefined)).toBe(2500)
    expect(auditRefetchInterval('queued')).toBe(2500)
    expect(auditRefetchInterval('running')).toBe(2500)
  })

  it('stops polling when the job is done or failed', () => {
    expect(auditRefetchInterval('done')).toBe(false)
    expect(auditRefetchInterval('failed')).toBe(false)
  })
})

describe('useAudit', () => {
  it('loads the state of the job and does not poll a finished one', async () => {
    respondJson(history[3])
    const { result } = renderHook(() => useAudit('abc'), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.state).toBe('done')
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('reports an unknown audit as an ApiError with the status', async () => {
    respondJson({ detail: 'Unknown audit.' }, 404)
    const { result } = renderHook(() => useAudit('abc'), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.error).toBeInstanceOf(ApiError)
    expect((result.current.error as ApiError).status).toBe(404)
  })
})

describe('useAuditResult', () => {
  it('does not ask the backend while it is disabled', () => {
    const { result } = renderHook(() => useAuditResult('abc', { enabled: false }), {
      wrapper: createWrapper(),
    })
    expect(result.current.fetchStatus).toBe('idle')
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('loads the result when it is enabled', async () => {
    respondJson(compliant)
    const { result } = renderHook(() => useAuditResult('abc', { enabled: true }), {
      wrapper: createWrapper(),
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.status).toBe('COMPLIANT')
  })

  it('reports a result that breaks the contract as a bad response', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    respondJson({ ...compliant, status: 'MAYBE' })
    const { result } = renderHook(() => useAuditResult('abc', { enabled: true }), {
      wrapper: createWrapper(),
    })
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect((result.current.error as ApiError).kind).toBe('bad_response')
  })
})