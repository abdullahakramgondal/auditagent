import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { auditKeys } from '@/api/queryKeys'
import { fetchMock, installFetchMock, respondJson } from '@/test/fetchMock'
import { createTestClient, createWrapper } from '@/test/queryWrapper'
import { useCreateAudit } from './useCreateAudit'

installFetchMock()

function pdf(name: string): File {
  return new File(['%PDF-1.4'], name, { type: 'application/pdf' })
}

const files = {
  contract: pdf('contract.pdf'),
  purchase_order: pdf('po.pdf'),
  invoice: pdf('invoice.pdf'),
}

describe('useCreateAudit', () => {
  it('starts the audit and gives back its id', async () => {
    respondJson({ audit_id: 'abc123' }, 202)
    const { result } = renderHook(() => useCreateAudit(), { wrapper: createWrapper() })
    await act(async () => {
      result.current.mutate({ files })
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.audit_id).toBe('abc123')
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('refreshes the history through its query key', async () => {
    respondJson({ audit_id: 'abc123' }, 202)
    const client = createTestClient()
    const invalidate = vi.spyOn(client, 'invalidateQueries')
    const { result } = renderHook(() => useCreateAudit(), { wrapper: createWrapper(client) })
    await act(async () => {
      result.current.mutate({ files })
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(invalidate).toHaveBeenCalledWith({ queryKey: auditKeys.list() })
  })

  it('reports a refused file as an error and does not refresh the history', async () => {
    respondJson({ detail: 'The invoice file is not a PDF.' }, 400)
    const client = createTestClient()
    const invalidate = vi.spyOn(client, 'invalidateQueries')
    const { result } = renderHook(() => useCreateAudit(), { wrapper: createWrapper(client) })
    await act(async () => {
      result.current.mutate({ files })
    })
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.error?.message).toBe('The invoice file is not a PDF.')
    expect(invalidate).not.toHaveBeenCalled()
  })
})