import { describe, expect, it, vi } from 'vitest'
import { z } from 'zod'
import { failNetwork, fetchMock, installFetchMock, respondJson, respondText } from '@/test/fetchMock'
import { ApiError, request } from './client'

installFetchMock()

const Thing = z.object({ name: z.string() })

/** Runs a call that must fail and hands back its ApiError. */
async function failure(call: Promise<unknown>): Promise<ApiError> {
  try {
    await call
  } catch (error) {
    if (error instanceof ApiError) return error
    throw error
  }
  throw new Error('the call was expected to fail')
}

describe('request', () => {
  it('asks the backend and returns the answer that matches the schema', async () => {
    respondJson({ name: 'abc' })
    const data = await request('/things', Thing)
    expect(data).toEqual({ name: 'abc' })
    expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/things')
  })

  it('passes the options to fetch', async () => {
    respondJson({ name: 'abc' })
    await request('/things', Thing, { method: 'POST' })
    expect(fetchMock.mock.calls[0][1]?.method).toBe('POST')
  })

  it('says that the service is not reachable when the network fails', async () => {
    failNetwork()
    const error = await failure(request('/things', Thing))
    expect(error.kind).toBe('network')
    expect(error.status).toBeNull()
    expect(error.message).toContain('not reachable')
  })

  it('uses the detail text of an error answer', async () => {
    respondJson({ detail: 'Unknown audit.' }, 404)
    const error = await failure(request('/things', Thing))
    expect(error.kind).toBe('http')
    expect(error.status).toBe(404)
    expect(error.message).toBe('Unknown audit.')
  })

  it('keeps the reason of a result that is not ready yet (409)', async () => {
    respondJson({ detail: 'The audit is running.' }, 409)
    const error = await failure(request('/things', Thing))
    expect(error.status).toBe(409)
    expect(error.message).toBe('The audit is running.')
  })

  it('does not show the list that a 422 carries', async () => {
    respondJson({ detail: [{ msg: 'field required', loc: ['body', 'contract'] }] }, 422)
    const error = await failure(request('/things', Thing))
    expect(error.status).toBe(422)
    expect(error.message).toBe('The service answered with an error (422).')
  })

  it('uses a general message when the error answer is not JSON', async () => {
    respondText('boom', 500)
    const error = await failure(request('/things', Thing))
    expect(error.kind).toBe('http')
    expect(error.message).toBe('The service answered with an error (500).')
  })

  it('refuses a 200 answer that is not JSON', async () => {
    respondText('<html>not the API</html>')
    const error = await failure(request('/things', Thing))
    expect(error.kind).toBe('bad_response')
  })

  it('refuses an answer that does not match the schema and logs why', async () => {
    const log = vi.spyOn(console, 'error').mockImplementation(() => {})
    respondJson({ name: 5 })
    const error = await failure(request('/things', Thing))
    expect(error.kind).toBe('bad_response')
    expect(log).toHaveBeenCalled()
  })

  it('is an Error that can be told apart by its class', async () => {
    failNetwork()
    const error = await failure(request('/things', Thing))
    expect(error).toBeInstanceOf(Error)
    expect(error.name).toBe('ApiError')
  })
})